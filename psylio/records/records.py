import logging
from operator import itemgetter

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from tqdm import tqdm

from ..routes import profile_url, records_url

logger = logging.getLogger(__name__)


@st.cache(hash_funcs={requests.Session: lambda _: None}, suppress_st_warning=True)
def retrieve_records(session):
    st.write('Retrieving records...')
    active_records = fetch_records(session)
    archived_records = fetch_records(session, is_archived=True)
    st.write(f'Found {len(active_records)} active records and {len(archived_records)} archived records!')

    active_records['Statut'] = 'Actif'
    archived_records['Statut'] = 'Archivé'

    records = pd.concat([active_records, archived_records])['Numéro']
    return records


def fetch_records(session, is_archived=False):
    converters = {
        'Numéro': itemgetter(0),
        'Titre': itemgetter(1),
    }

    resp = session.get(records_url(is_archived))
    records = pd.read_html(resp.content, converters=converters, extract_links='body')[0]

    records['Url'] = records['Titre'].str.split('/+', regex=True)
    records['RecordID'] = records['Url'].apply(itemgetter(3))
    
    return records.set_index('RecordID')


@st.cache(hash_funcs={requests.Session: lambda _: None})
def get_record_infos_from_ids(session, record_ids):
    records = []
    for record_id in tqdm(record_ids):
        resp = session.get(profile_url(record_id))
        soup = BeautifulSoup(resp.content, 'html.parser')

        columns = ['RecordID', 'Client 1', 'Courriel 1', 'Client 2', 'Courriel 2']
        record_infos = dict.fromkeys(columns, "")
        record_infos['RecordID'] = record_id

        tabpanels = soup.find_all('div', {'role': 'tabpanel'})
        for i, tabpanel in enumerate(tabpanels):
            full_name, email = extract_person_infos(session, tabpanel)
            record_infos[f"Client {i + 1}"] = full_name
            record_infos[f"Courriel {i + 1}"] = email

        records.append(record_infos)

    records = pd.DataFrame(records)
    records.set_index('RecordID', inplace=True)
    return records


def extract_person_infos(session, tabpanel):
    person_url = tabpanel.find('a', {'class': 'btn-outline-secondary'}).get('href')
    resp = session.get(person_url)

    soup = BeautifulSoup(resp.content, 'html.parser')

    first_name = soup.find('input', {'id': 'firstname'}).get('value')
    last_name = soup.find('input', {'id': 'lastname'}).get('value')
    full_name = ', '.join([last_name, first_name])

    email = soup.find('input', {'id': 'email'}).get('value')

    return full_name, email
