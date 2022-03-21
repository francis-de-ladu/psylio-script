import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

from ..utils import request_confirm

logger = logging.getLogger(__name__)


def close_paid_invoices(email, password, unpaid_df, newly_paid_df):
    columns = ['Facture', 'Date', 'Client 1', 'Montant dû', 'Date paiement']
    print(newly_paid_df[columns])
    request_confirm(f'Mark {len(newly_paid_df)} invoice(s) as paid?')

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

    # reindex dataframes
    unpaid_df = unpaid_df.reset_index().set_index('Facture')
    newly_paid_df = newly_paid_df.set_index('Facture')

    # get newly paid invoices
    columns = ['Date paiement', 'Comptant', 'Interac']
    to_close_df = newly_paid_df[columns].join(unpaid_df, on='Facture')

    # mark invoices as paid and send receipts
    for _, invoice in to_close_df.iterrows():
        logger.info(f'Closing invoice {invoice.name}...')
        close_invoice(driver, invoice)

    time.sleep(3)
    driver.quit()


def close_invoice(driver, invoice):
    # open invoice page
    record_id, invoice_id = invoice[['record_id', 'invoice_id']]
    base_url = 'https://admin.psylio.com/assistance-requests'
    invoice_url = f'{base_url}/{record_id}/invoices/{invoice_id}'
    driver.get(invoice_url)

    # get invoice infos
    payment_date = invoice['Date paiement']
    payment_types = 'debit_transfer' if invoice['Interac'] else 'cash'

    # mark invoice as paid
    mark_invoice_as_paid(driver, payment_date, payment_types)
    time.sleep(2)

    # send invoice receipt
    send_invoice_receipt(driver, invoice_url)


def mark_invoice_as_paid(driver, payment_date, payment_types):
    # open the form
    mark_as_paid_btn = driver.find_element(
        By.XPATH, '//a[@data-target="#mark-as-paid-modal"]')
    mark_as_paid_btn.click()
    time.sleep(1)

    # select the form
    mark_as_paid_form = driver.find_element(
        By.XPATH, '//form[@class="paymentType"]')

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
