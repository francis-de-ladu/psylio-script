import logging
from datetime import datetime, timedelta
from operator import itemgetter

import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

from ..routes import open_invoices_url, record_invoices_url

logger = logging.getLogger(__name__)


def retrieve_open_invoices(session, nb_days=60):
    columns = ['Service(s)', 'Facturé le', 'Montant dû', 'État', 'Unnamed: 6']
    converters = {col: itemgetter(0) for col in columns}

    logger.info('Retrieving open invoices...')
    resp = session.get(open_invoices_url(nb_days))

    # TODO: handle possible exception
    open_invoices = pd.read_html(resp.content, converters=converters, extract_links='body')[1]

    # extract record/invoice IDs
    open_invoices[['Facture', 'invoice_url']] = open_invoices['Facture'].tolist()
    # Invoice URL format: https://admin.psylio.com/assistance-requests/<record_id>/invoices/<invoice_id>
    open_invoices['invoice_url'] = open_invoices['invoice_url'].str.split('/+', regex=True)
    open_invoices['RecordID'] = open_invoices['invoice_url'].apply(itemgetter(3))
    open_invoices['InvoiceID'] = open_invoices['invoice_url'].apply(itemgetter(5))
        
    STATES = ('Brouillon', 'Facture envoyée')  # , 'Payée', 'Reçu envoyé')
    open_invoices['État'] = open_invoices.iloc[:, 6].apply(
        lambda dropdown: STATES[0] if 'Marquer envoyée' in dropdown else STATES[1]
    )

    columns = {
        'RecordID': 'RecordID',
        'Facture': 'Facture',
        'InvoiceID': 'InvoiceID',
        'Service(s)': 'Service(s)',
        'Facturé le': 'Date',
        'Montant dû': 'Montant',
        'État': 'État',
    }

    open_invoices = open_invoices[list(columns)]
    open_invoices.rename(columns=columns, inplace=True)

    INDEX_COLS = ['RecordID', 'Date']
    open_invoices.set_index(INDEX_COLS, inplace=True)

    return open_invoices


def retrieve_paid_invoices(session, record_ids):
    columns = {
        'RecordID': 'RecordID',
        'Facture': 'Facture',
        'Service(s)': 'Service(s)',
        'Facturé le': 'Date',
        'Montant payé': 'Montant',
        'État': 'État',
    }

    logger.info('Retrieving paid invoices...')

    paid_invoices = []
    for record_id in tqdm(record_ids):
        resp = session.get(record_invoices_url(record_id, state='paid'))

        try:
            record_invoices = pd.read_html(resp.content)[0]
            record_invoices['RecordID'] = record_id
            record_invoices = record_invoices[list(columns)]
        except ValueError:
            logger.error("EXCEPTION!")
            record_invoices = pd.DataFrame(columns=list(columns))
        finally:
            paid_invoices.append(record_invoices)

    paid_invoices = pd.concat(paid_invoices)
    paid_invoices.rename(columns=columns, inplace=True)

    INDEX_COLS = ['RecordID', 'Date']
    paid_invoices.set_index(INDEX_COLS, inplace=True)
    # paid_invoices.set_index('RecordID', inplace=True)

    return paid_invoices


def fetch_invoices(session, record_id, state=None):
    segments = ['assistance-requests', record_id, 'invoices']
    endpoint = endpoint_url(*segments, state=state)
    resp = session.get(endpoint)

    KEEP_COLS = ['Facture', 'Service(s)', 'Facturé le', 'Montant', 'État']

    try:
        invoices = pd.read_html(resp.content)[0]
        invoices.rename(columns={'Montant payé': 'Montant'}, inplace=True)
        invoices = invoices[KEEP_COLS]
    except ValueError:
        invoices = pd.DataFrame(columns=KEEP_COLS)
    finally:
        return invoices


def retrieve_invoices(session, appointments, nb_days=30):
    # TODO: ?types=income&start=2022-03-07&end=2022-03-21
    #       &date_type=manual&categories=<service_code_here>
    logger.info('Retrieving invoices...')

    paid_invoices = []
    for record_id in appointments.index.unique(level=0):
        client_invoices = fetch_invoices(session, record_id, state='paid')
        client_invoices['RecordID'] = record_id
        paid_invoices.append(client_invoices)

    KEEP_COLS = ['RecordID', 'Facture', 'Service(s)', 'Facturé le', 'Montant dû', 'État']
    converters = {col: itemgetter(0) for col in KEEP_COLS[2:] + ['Unnamed: 6']}

    # fetch open invoices (those already created, but not paid)
    open_invoices = retrieve_open_invoices(session, nb_days)

    invoices = pd.concat([open_invoices, *paid_invoices])
    invoices.rename(columns={'Facturé le': 'Date'}, inplace=True)

    new_index = ['RecordID', 'Date']
    invoices.set_index(new_index, inplace=True)

    # normalize `amount` column, then convert to float
    invoices['Montant'] = invoices['Montant'].str.strip('\xa0 $')
    invoices['Montant'] = invoices['Montant'].str.replace(',', '.')
    invoices['Montant'] = invoices['Montant'].astype(float)

    logging.info(f'Found a total of {len(invoices)} invoices!')

    return invoices


def retrieve_invoices_old(session, records_df):
    # TODO: ?types=income&start=2022-03-07&end=2022-03-21
    #       &date_type=manual&categories=<service_code_here>
    logger.info('Retrieving invoices...')

    all_invoices = []
    for record_id, _ in records_df.iterrows():
        record_invoices = get_record_invoices(session, record_id)
        all_invoices.append(record_invoices)

    invoices_df = pd.concat(all_invoices)
    invoices_df.rename(columns={'Facturé le': 'Date'}, inplace=True)

    new_index = ['record_id', 'Date']
    invoices_df.set_index(new_index, inplace=True)

    columns = ['invoice_id', 'Facture', 'Service(s)', 'État', 'Montant dû', 'Montant payé']
    invoices_df = invoices_df[columns]

    logging.info(f'Found a total of {len(invoices_df)} invoices!')

    return invoices_df


def get_record_invoices(session, record_id):

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

    # get paid and unpaid invoices for the record
    unpaid_df = helper(endpoint)
    paid_df = helper(f'{endpoint}?state=paid')

    # concat and return both dataframes
    invoices_df = pd.concat([unpaid_df, paid_df])
    return invoices_df


def retrieve_unpaid_invoices(session):
    logger.info('Retrieving unpaid invoices (including newly created)...')

    # get unpaid invoices
    unpaid_df = retrieve_open_invoices(session)

    # drop useless columns
    columns = ['Facture', 'Service(s)', 'Montant', 'InvoiceID']
    unpaid_df = unpaid_df[columns]

    logger.info(f'Found {len(unpaid_df)} unpaid invoices!')

    return unpaid_df

def retrieve_unpaid_invoices_old(session):
    logger.info('Retrieving unpaid invoices (including newly created)...')

    # get unpaid invoices
    unpaid_df = retrieve_open_invoices(session)
    unpaid_df.rename(columns={'Facturé le': 'Date'}, inplace=True)

    # set new index columns
    new_index = ['record_id', 'Date']
    unpaid_df.set_index(new_index, inplace=True)

    # drop useless columns
    columns = ['Facture', 'Service(s)', 'Montant dû', 'invoice_id']
    unpaid_df = unpaid_df[columns]

    logger.info(f'Found {len(unpaid_df)} unpaid invoices!')

    return unpaid_df


def retrieve_open_invoices_old(session):
    page = 1
    unpaid_pages = []

    while True:
        # fetch next page
        resp = session.get(f'https://admin.psylio.com/invoices?page={page}')

        try:
            # extract invoices from html
            page_df = pd.read_html(resp.text)[1]
        except IndexError:
            # all pages have been fetched
            break

        # parse html
        soup = BeautifulSoup(resp.content, 'html.parser')

        # for each invoice, extract invoice link
        links = soup.find_all('a', {'data-target': '#mark-as-paid-modal'})
        links = [link.get('data-route') for link in links]

        # extract record_id and invoice_id for each invoice from its link
        links = [link.split('/') for link in links]
        record_ids = [link[4] for link in links]
        invoice_ids = [link[6] for link in links]

        # update dataframe
        page_df['record_id'] = record_ids
        page_df['invoice_id'] = invoice_ids

        # save resulting dataframe and update page number
        unpaid_pages.append(page_df)
        page += 1

    return pd.concat(unpaid_pages)
