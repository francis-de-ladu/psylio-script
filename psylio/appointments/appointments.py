import logging
from datetime import datetime, timedelta
from functools import reduce
from operator import getitem

import pandas as pd

from ..utils import get_endpoint_url

logger = logging.getLogger(__name__)


def get_appointments(session, days=30):
    end = datetime.now()
    start = end - timedelta(days=days)

    segments = ['appointments', 'agenda', 'calendar']
    endpoint = get_endpoint_url(*segments, start=start, end=end)

    columns = dict(
        startDate='Date',
        startHour='Heure',
        assistanceRequest_data_id='DossierID',
        title='Titre',
    )

    logger.info('Getting appointments...')
    resp = session.get(endpoint)

    appointments = []
    for entry in resp.json():
        data = entry['modal']['appointment']
        # infos = {key: data[key] for key in columns}
        infos = {key: reduce(getitem, key.split('_'), data) for key in columns}
        appointments.append(infos)

    appointments = pd.DataFrame(appointments)
    appointments.rename(columns=columns, inplace=True)

    INDEX_COLS = ['DossierID', 'Date']
    appointments.sort_values(INDEX_COLS, inplace=True)
    appointments.set_index(INDEX_COLS, inplace=True)

    logger.info((f'Found {len(appointments)} appointments '
                 f'over last {days} days!'))

    mask = ~appointments['Titre'].str.contains('annulé')
    appointments = appointments.loc[mask]

    return appointments


def get_appointments_old(session, records_df, days=30):
    end = datetime.now()
    start = end - timedelta(days=days)

    base_url = 'https://admin.psylio.com/appointments/agenda/calendar'
    endpoint = f'{base_url}?start={start.date()}&end={end.date()}'
    resp = session.get(endpoint)

    columns = {
        'startDate': 'Date',
        'startHour': 'Heure début',
        'endHour': 'Heure fin',
    }

    logger.info('Getting appointments...')

    appointments = []
    for appoint in resp.json():
        appoint = appoint['modal']['appointment']
        record_id = appoint['assistanceRequest']['data']['id']

        infos = {col: appoint[key] for key, col in columns.items()}
        infos['record_id'] = record_id

        appointments.append(infos)

    new_index = ['record_id', 'Date']
    appoints_df = pd.DataFrame(appointments).sort_values(
        by=new_index, ascending=False)

    appoints_df.set_index(new_index, inplace=True)
    appoints_df = appoints_df.join(records_df, on='record_id')

    appoint_cnt = len(appointments)
    logger.info(f'Found {appoint_cnt} appointments over last {days} days!')

    return appoints_df
