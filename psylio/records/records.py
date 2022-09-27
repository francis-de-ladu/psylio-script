import requests
import logging

import pandas as pd
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

from ..routes import profile_url, records_url

logger = logging.getLogger(__name__)


def retrieve_records_from_list(session, record_ids):
    records = []
    for record_id in record_ids:
        resp = session.get(profile_url(record_id))
        soup = BeautifulSoup(resp.content, 'html.parser')

        columns = ['RecordID', 'Client 1', 'Courriel 1', 'Client 2', 'Courriel 2']
        record_infos = pd.DataFrame(columns=columns)
        record_infos['RecordID'] = record_id

        tabpanels = soup.find_all('div', {'role': 'tabpanel'})
        for i, tabpanel in enumerate(tabpanels):
            full_name, email = extract_person_infos(session, tabpanel)
            record_infos[[f'Client {i + 1}', f'Courriel {i + 1}']] = full_name, email

        records.append(record_infos)

    return pd.concat(records)


def extract_person_infos(session, tabpanel):
    person_url = tabpanel.find('a', {'class': 'btn-outline-secondary'}).get('href')
    resp = session.get(person_url)

    soup = BeautifulSoup(resp.content, 'html.parser')

    first_name = soup.find('input', {'id': 'firstname'}).get('value')
    last_name = soup.find('input', {'id': 'lastname'}).get('value')
    full_name = ', '.join([last_name, first_name])

    email = soup.find('input', {'id': 'email'}).get('value')

    return full_name, email


def get_records_old(session):
    logger.info('Retrieving records...')
    active_records = fetch_records(session)
    archived_records = fetch_records(session, is_archived=True)
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
    logger.info('Retrieving records...')
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


def fetch_records(session, is_archived=False):
    resp = session.get(records_url(is_archived))
    # records = pd.read_html(resp.content)[0]
    # print(records.columns)
    # print(records)

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
