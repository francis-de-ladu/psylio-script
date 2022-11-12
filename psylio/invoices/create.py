import json
import logging
import re
from itertools import pairwise

import requests
import streamlit as st
from bs4 import BeautifulSoup

from psylio.routes.routes import invoice_url, record_invoices_url

from ..utils import request_confirm

logger = logging.getLogger(__name__)


@st.cache(hash_funcs={requests.Session: lambda _: None})
def create_missing_invoices(session, missing_invoices):
    logger.info('Creating invoices for appointments not having one already...')

    if missing_invoices.empty:
        logger.info('There were no missing invoices.')
    else:
        print(missing_invoices[['Heure', 'Titre']])
        request_confirm(f'The above {len(missing_invoices)} invoice(s) will be created, is this correct?')

    missing_invoices.reset_index(inplace=True, drop=False)
    for _, invoice in missing_invoices.iterrows():
        create_invoice(session, invoice)


def create_invoice(session, invoice, service='Sexologie psychothérapie'):
    record_id, appoint_date, start_time = invoice[['RecordID', 'Date', 'Heure']]
    logger.info(f'Creating invoice for {appoint_date} at {start_time}...')

    resp = session.get(invoice_url(record_id, create=True))
    soup = BeautifulSoup(resp.content, 'html.parser')
    invoice_form = soup.find('form', attrs={'class': 'form invoice'})

    payload = {}

    # add values of `input` elements to payload
    for field in invoice_form.find_all('input'):
        field_name, field_value = field.get('name'), field.get('value', '')
        if field_name:
            add_to_payload(payload, field_name, field_value)

    # add values of `textarea` elements to payload
    for field in invoice_form.find_all('textarea'):
        field_name, field_value = field.get('name'), field.get_text()
        add_to_payload(payload, field_name, field_value)

    # add missing fields to payload
    payload['institution'] = {'id': ''}
    payload['paymentDate'] = ''
    payload['paymentTypes'] = ''

    # update client names and billing date
    client_names = ' et '.join(filter(bool, invoice[['Client 1', 'Client 2']]))
    payload['meta']['billed_to_name'] = client_names
    payload['meta']['client_name'] = client_names
    payload['meta']['charged_at'] = appoint_date

    # format `price` entry
    price_per_unit = payload['items']['0']['price_per_unit'].replace(',', '.')
    payload['items']['0'].update({
        'service': service,
        'price_per_unit': price_per_unit,
    })

    # create invoice
    session.post(record_invoices_url(record_id), data=json.dumps(payload))


def add_to_payload(payload, field_name, field_value, pattern=r'(\[|\]|\]\[])'):
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


# def pairwise(iterable):
#     # pairwise('ABCDEFG') --> AB BC CD DE EF FG
#     a, b = tee(iterable)
#     next(b, None)
#     return zip(a, b)
