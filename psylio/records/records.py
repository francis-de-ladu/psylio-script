import logging

import pandas as pd
from bs4 import BeautifulSoup

from ..routes import records_url, profile_url

logger = logging.getLogger(__name__)


def get_records_old(session):
    logger.info('Getting records...')
    active_records = fetch_records(session)
    archived_records = fetch_records(session, archive=True)
    logger.info(f'Found {len(active_records)} active records'
                f' and {len(archived_records)} archived records!')

    active_records['Statut'] = 'Actif'
    archived_records['Statut'] = 'Archivé'

    columns = ['Numéro de dossier', 'Statut', 'Client 1',
               'Courriel 1', 'Client 2', 'Courriel 2']

    records_df = pd.concat([active_records, archived_records])
    records_df = records_df[columns]

    return records_df


def fetch_records_old(session, base_url, endpoint=None):
    endpoint = '/'.join([base_url, endpoint]) if endpoint else base_url
    resp = session.get(endpoint)

    soup = BeautifulSoup(resp.content, 'html.parser')
    tbody = soup.find('table').tbody

    record_ids = []
    for row in tbody.find_all('tr'):
        cells = row.find_all('td')
        rid = cells[1].a.get('href').split('/')[4]
        record_ids.append(rid)

    records_df = pd.read_html(resp.text)[0]
    records_df[['Client 2', 'Courriel 2']] = ''

    records_df['record_id'] = record_ids
    records_df.set_index('record_id', inplace=True)

    for record_id, record in records_df.iterrows():
        profile_url = f'{base_url}/{record_id}/profile'
        resp = session.get(profile_url)

        soup = BeautifulSoup(resp.content, 'html.parser')
        clients = soup.find(
            'div', {'class': 'tab-content profile-informations clearfix'})

        tabs = clients.find_all('div', {'role': 'tabpanel'})
        for i, client in enumerate(tabs):
            person_link = client.find('a').get('href')
            resp = session.get(person_link)

            soup = BeautifulSoup(resp.content, 'html.parser')

            fname = soup.find('input', {'id': 'firstname'}).get('value')
            lname = soup.find('input', {'id': 'lastname'}).get('value')
            email = soup.find('input', {'id': 'email'}).get('value')

            records_df.loc[record_id, f'Client {i + 1}'] = f'{lname}, {fname}'
            records_df.loc[record_id, f'Courriel {i + 1}'] = email

    return records_df


def get_records(session):
    logger.info('Getting records...')
    active_records = fetch_records(session)
    archived_records = fetch_records(session, endpoint='archive')
    logger.info(f'Found {len(active_records)} active records'
                f' and {len(archived_records)} archived records!')

    active_records['Statut'] = 'Actif'
    archived_records['Statut'] = 'Archivé'

    columns = ['Numéro de dossier', 'Statut', 'Client 1',
               'Courriel 1', 'Client 2', 'Courriel 2']

    records_df = pd.concat([active_records, archived_records])
    records_df = records_df[columns]

    return records_df


def fetch_records(session, archive=False):
    resp = session.get(records_url(archive))
    records = pd.read_html(resp.content)[0]
    print(records.columns)
    print(records)

    soup = BeautifulSoup(resp.content, 'html.parser')
    tbody = soup.find('table').tbody

    record_ids = []
    for row in tbody.find_all('tr'):
        cells = row.find_all('td')
        rid = cells[1].a.get('href').split('/')[4]
        record_ids.append(rid)

    records_df = pd.read_html(resp.text)[0]
    records_df[['Client 2', 'Courriel 2']] = ''

    records_df['record_id'] = record_ids
    records_df.set_index('record_id', inplace=True)

    for record_id, record in records_df.iterrows():
        resp = session.get(profile_url(record_id))

        soup = BeautifulSoup(resp.content, 'html.parser')
        clients = soup.find(
            'div', {'class': 'tab-content profile-informations clearfix'})

        tabs = clients.find_all('div', {'role': 'tabpanel'})
        for i, client in enumerate(tabs):
            person_link = client.find('a').get('href')
            resp = session.get(person_link)

            soup = BeautifulSoup(resp.content, 'html.parser')

            fname = soup.find('input', {'id': 'firstname'}).get('value')
            lname = soup.find('input', {'id': 'lastname'}).get('value')
            email = soup.find('input', {'id': 'email'}).get('value')

            records_df.loc[record_id, f'Client {i + 1}'] = f'{lname}, {fname}'
            records_df.loc[record_id, f'Courriel {i + 1}'] = email

    return records_df
