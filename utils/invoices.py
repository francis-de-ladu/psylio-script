import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib
import webbrowser
from base64 import b64encode
from collections import defaultdict
from datetime import datetime, timedelta
from itertools import tee

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager


def get_invoices(session, records_df):
    all_invoices = []
    for record_id, _ in records_df.iterrows():
        record_invoices = get_invoices_for_record(session, record_id)
        all_invoices.append(record_invoices)

    invoices_df = pd.concat(all_invoices)

    invoices_df.rename(columns={'Facturé le': 'Date'}, inplace=True)

    new_index = ['record_id', 'Date']
    invoices_df.set_index(new_index, inplace=True)

    columns = ['invoice_id', 'Facture',
               'Service(s)', 'État', 'Montant dû', 'Montant payé']
    invoices_df = invoices_df[columns]

    return invoices_df


def get_invoices_for_record(session, record_id):

    def helper(endpoint):
        try:
            resp = session.get(endpoint)
            soup = BeautifulSoup(resp.content, 'html.parser')
            tbody = soup.find('table').tbody

            invoice_ids = []
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                iid = cells[0].a.get('href').split('/')[6]
                invoice_ids.append(iid)

            invoices_df = pd.read_html(resp.text)[0]
            invoices_df['invoice_id'] = invoice_ids
            invoices_df['record_id'] = record_id
        except AttributeError:
            invoices_df = pd.DataFrame()

        return invoices_df

    base_url = 'https://admin.psylio.com/assistance-requests'
    endpoint = f'{base_url}/{record_id}/invoices'

    unpaid_df = helper(endpoint)
    paid_df = helper(f'{endpoint}?state=paid')

    return pd.concat([unpaid_df, paid_df])


def create_missing_invoices(session, appoints_df, invoices_df):
    invoices_df = appoints_df.join(invoices_df, on=['record_id', 'Date'])
    invoices_df = invoices_df.reset_index()

    invoices_df.sort_values(['Date', 'Heure début'], inplace=True)
    missing_invoices = invoices_df.loc[invoices_df['Facture'].isna()]

    for i, invoice in missing_invoices.iterrows():
        create_invoice(session, invoice)


def create_invoice(session, invoice):
    record_id = invoice['record_id']
    base_url = 'https://admin.psylio.com/assistance-requests'
    endpoint = f'{base_url}/{record_id}/invoices'

    resp = session.get(f'{endpoint}/create')
    soup = BeautifulSoup(resp.content, 'html.parser')
    forms = soup.find_all('form')

    client_names = ' et '.join(filter(bool, invoice[['Client 1', 'Client 2']]))

    payload = {}

    for field in forms[1].find_all('input'):
        field_name, field_value = field.get('name'), field.get('value', '')
        if field_name is not None:
            add_to_payload(payload, field_name, field_value)

    for field in forms[1].find_all('textarea'):
        field_name, field_value = field.get('name'), field.get_text()
        add_to_payload(payload, field_name, field_value)

    payload['institution'] = {'id': ''}
    # payload['paymentDate'] = str(datetime.today()).split()[0]
    # payload['paymentTypes'] = ','.join(['debit_transfer'])
    payload['paymentDate'] = ''
    payload['paymentTypes'] = ''
    payload['meta']['charged_at'] = invoice['Date']
    payload['meta']['client_name'] = client_names
    payload['meta']['billed_to_name'] = client_names
    payload['items']['0'].update({
        'service': 'Suivi client',
        'price_per_unit': payload['items']['0']['price_per_unit'].replace(',', '.'),
    })

    resp = session.post(endpoint, data=json.dumps(payload))
    # TODO: logger.info(f'ended with status code: {resp.status_code}')


def add_to_payload(payload, field_name, field_value, pattern=r'(\[|\]|\]\[])'):

    def pairwise(iterable):
        # pairwise('ABCDEFG') --> AB BC CD DE EF FG
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    keys = re.sub(pattern, ' ', field_name).split()
    if len(keys) == 1:
        payload[field_name] = field_value
    else:
        current = payload
        for k1, k2 in pairwise(keys):
            if k1 in current:
                current = current[k1]
            else:
                current[k1] = {}
                current = current[k1]

        current[k2] = field_value


def get_unpaid_invoices(session):
    dfs = []
    page = 1

    columns = {
        'record_id': 'record_id',
        'Facturé le': 'Date',
        'Facture': 'Facture',
        'Service(s)': 'Service(s)',
        'Montant dû': 'Montant dû',
        'invoice_id': 'invoice_id',
    }

    while True:
        # fetch next page
        resp = session.get(f'https://admin.psylio.com/invoices?page={page}')

        # extract invoices from html
        df = pd.read_html(resp.text)

        # break if page doesn't contain any invoice
        if len(df) < 2:
            break

        # parse page html
        soup = BeautifulSoup(resp.content, 'html.parser')

        # for each invoice, extract invoice link
        links = soup.find_all('a', {'data-target': '#mark-as-paid-modal'})
        links = [link.get('data-route') for link in links]

        # extract record_id and invoice_id for each invoice
        links = [link.split('/') for link in links]
        record_ids = [link[4] for link in links]
        invoice_ids = [link[6] for link in links]

        # update dataframe
        df = df[1]
        df['record_id'] = record_ids
        df['invoice_id'] = invoice_ids

        # save dataframe and update page number
        dfs.append(df)
        page += 1

    # merge dataframes and reorder columns
    unpaid_df = pd.concat(dfs)
    unpaid_df = unpaid_df[list(columns.keys())]

    # rename columns and set index
    unpaid_df.rename(columns=columns, inplace=True)
    unpaid_df.set_index(['record_id', 'Date'], inplace=True)

    return unpaid_df


def close_invoice(driver, invoice):
    print(invoice)
    # open invoice page
    record_id, invoice_id = invoice[['record_id', 'invoice_id']]
    base_url = 'https://admin.psylio.com/assistance-requests'
    invoice_url = f'{base_url}/{record_id}/invoices/{invoice_id}'
    driver.get(invoice_url)

    # get invoice infos
    payment_date = invoice['Date paiement']
    payment_types = 'debit_transfer' if invoice['Interac'] else 'cash'
    # payment_date, payment_types = invoice[['Date paiement', 'paymentTypes']]

    try:
        # mark invoice as paid
        mark_invoice_as_paid(driver, payment_date, payment_types)
        time.sleep(2)
    except Exception:
        pass

    try:
        # send invoice receipt
        # emails = ', '.join(filter(bool, invoice[['Courriel 1', 'Courriel 2']]))
        send_invoice_receipt(driver, invoice_url)
    except Exception:
        pass


def mark_invoice_as_paid(driver, payment_date, payment_types):
    # open the form
    mark_as_paid_btn = driver.find_element(
        By.XPATH, '//a[@data-target="#mark-as-paid-modal"]')
    mark_as_paid_btn.click()
    time.sleep(1)

    # select the form
    mark_as_paid_form = driver.find_element(
        By.XPATH, f'//form[@class="paymentType"]')

    # set payment date
    date_field = mark_as_paid_form.find_element(
        By.XPATH, '//input[@name="paymentDate"]')
    driver.execute_script("arguments[0].value = ''", date_field)
    date_field.send_keys(str(payment_date))
    date_field.send_keys(Keys.RETURN)

    # set payment type
    type_field = mark_as_paid_form.find_element(
        By.XPATH, f'//input[@name="paymentTypes[{payment_types}]"]')
    type_field.click()

    # submit the form
    mark_as_paid_form.submit()


def send_invoice_receipt(driver, invoice_url):
    # open the form
    send_receipt_btn = driver.find_element(
        By.XPATH, '//a[@data-target="#send-receipt-by-email-modal"]')
    send_receipt_btn.click()
    time.sleep(1)

    # select and submit the form
    send_receipt_form = driver.find_element(
        By.XPATH, f'//form[@action="{invoice_url}/receipt/email"]')
    send_receipt_form.submit()


def close_paid_invoices(email, password, unpaid_df, newly_paid_df):
    # instantiate driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.get('https://admin.psylio.com')

    login_form = driver.find_element(
        By.XPATH, '//form[@action="https://admin.psylio.com/login"]')

    email_field = login_form.find_element(
        By.XPATH, '//input[@name="login[email]"]')
    password_field = login_form.find_element(
        By.XPATH, '//input[@name="login[password]"]')

    email_field.send_keys(email)
    password_field.send_keys(password)

    login_form.submit()

    # get newly paid invoices
    columns = ['Date paiement', 'Comptant', 'Interac']
    to_finalize_df = newly_paid_df[columns].join(unpaid_df, on='Facture')

    # mark invoices as paid and send receipts
    for _, invoice in to_finalize_df.iterrows():
        close_invoice(driver, invoice)

    time.sleep(3)
    driver.quit()
