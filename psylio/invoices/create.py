import json
import logging
import re
from itertools import tee

from bs4 import BeautifulSoup

from psylio.routes.routes import record_invoices_url

from ..utils import request_confirm

logger = logging.getLogger(__name__)


def create_missing_invoices(session, missing_invoices):
    logger.info('Creating invoices for appointments without one...')

    if missing_invoices.empty:
        logger.info('There were no missing invoices.')
    else:
        print(missing_invoices[['Heure', 'Titre']])
        request_confirm(f'The above {len(missing_invoices)} invoice(s) will be created, is this correct?')

    missing_invoices.reset_index(inplace=True, drop=False)
    for _, invoice in missing_invoices.iterrows():
        create_invoice(session, invoice)


def create_invoice(session, invoice, service='Sexologie psychothérapie'):
    date, start_time = invoice[['Date', 'Heure début']]
    logger.info(f'Creating invoice for {date} at {start_time}...')

    resp = session.get(record_invoices_url(invoice['RecordID']))
    soup = BeautifulSoup(resp.content, 'html.parser')
    forms = soup.find_all('form')

    payload = {}

    # add values of `input` elements to payload
    for field in forms[1].find_all('input'):
        field_name, field_value = field.get('name'), field.get('value', '')
        if field_name is not None:
            add_to_payload(payload, field_name, field_value)

    # add values of `textarea` elements to payload
    for field in forms[1].find_all('textarea'):
        field_name, field_value = field.get('name'), field.get_text()
        add_to_payload(payload, field_name, field_value)

    # add missing fields to payload
    payload['institution'] = {'id': ''}
    payload['paymentDate'] = ''
    payload['paymentTypes'] = ''
    payload['meta']['charged_at'] = invoice['Date']

    # update client names
    client_names = ' et '.join(filter(bool, invoice[['Client 1', 'Client 2']]))
    payload['meta']['client_name'] = client_names
    payload['meta']['billed_to_name'] = client_names

    # format `price` entry
    price_per_unit = payload['items']['0']['price_per_unit'].replace(',', '.')
    payload['items']['0'].update({
        'service': service,
        'price_per_unit': price_per_unit,
    })

    # create invoice
    session.post(endpoint, data=json.dumps(payload))


def create_invoice_old(session, invoice, service='Sexologie psychothérapie'):
    date, start_time = invoice[['Date', 'Heure']]
    logger.info(f'Creating invoice for {date} at {start_time}...')

    record_id = invoice['RecordID']
    base_url = 'https://admin.psylio.com/assistance-requests'
    endpoint = f'{base_url}/{record_id}/invoices'

    resp = session.get(f'{endpoint}/create')
    soup = BeautifulSoup(resp.content, 'html.parser')
    forms = soup.find_all('form')

    payload = {}

    # add values of `input` elements to payload
    for field in forms[1].find_all('input'):
        field_name, field_value = field.get('name'), field.get('value', '')
        if field_name is not None:
            add_to_payload(payload, field_name, field_value)

    # add values of `textarea` elements to payload
    for field in forms[1].find_all('textarea'):
        field_name, field_value = field.get('name'), field.get_text()
        add_to_payload(payload, field_name, field_value)

    # add missing fields to payload
    payload['institution'] = {'id': ''}
    payload['paymentDate'] = ''
    payload['paymentTypes'] = ''
    payload['meta']['charged_at'] = invoice['Date']

    # update client names
    client_names = ' et '.join(filter(bool, invoice[['Client 1', 'Client 2']]))
    payload['meta']['client_name'] = client_names
    payload['meta']['billed_to_name'] = client_names

    # format `price` entry
    price_per_unit = payload['items']['0']['price_per_unit'].replace(',', '.')
    payload['items']['0'].update({
        'service': service,
        'price_per_unit': price_per_unit,
    })

    # create invoice
    session.post(endpoint, data=json.dumps(payload))


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


def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)
