import logging

import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def retrieve_invoices(session, records_df):
    # TODO: ?types=income&start=2022-03-07&end=2022-03-21
    #       &date_type=manual&categories=<service_code_here>
    logger.info('Getting invoices...')

    all_invoices = []
    for record_id, _ in records_df.iterrows():
        record_invoices = get_record_invoices(session, record_id)
        all_invoices.append(record_invoices)

    invoices_df = pd.concat(all_invoices)
    invoices_df.rename(columns={'Facturé le': 'Date'}, inplace=True)

    new_index = ['record_id', 'Date']
    invoices_df.set_index(new_index, inplace=True)

    columns = ['invoice_id', 'Facture',
               'Service(s)', 'État', 'Montant dû', 'Montant payé']
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


def get_unpaid_invoices(session):
    logger.info('Retrieving unpaid invoices (including newly created)...')

    # get unpaid invoices
    unpaid_df = fetch_unpaid(session)
    unpaid_df.rename(columns={'Facturé le': 'Date'}, inplace=True)

    # set new index columns
    new_index = ['record_id', 'Date']
    unpaid_df.set_index(new_index, inplace=True)

    # drop useless columns
    columns = ['Facture', 'Service(s)', 'Montant dû', 'invoice_id']
    unpaid_df = unpaid_df[columns]

    logger.info(f'Found {len(unpaid_df)} unpaid invoices!')

    return unpaid_df


def fetch_unpaid(session):
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
