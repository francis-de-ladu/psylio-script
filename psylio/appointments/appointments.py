import logging
from functools import reduce
from operator import getitem

import pandas as pd
import streamlit as st

from ..routes import appointments_url

logger = logging.getLogger(__name__)


@st.cache_data()
def retrieve_appointments(_session, records, nb_days=30):
    columns = dict(
        startDate='Date',
        startHour='Heure',
        assistanceRequest__data__id='RecordID',
        title='Titre',
    )

    st.write('Retrieving appointments...')
    resp = _session.get(appointments_url(nb_days))

    # retrieve appointments from response
    appointments = []
    for entry in resp.json():
        data = entry['data']['appointment']
        infos = {key: reduce(getitem, key.split('__'), data) for key in columns}
        appointments.append(infos)

    # convert to a DataFrame and rename the columns
    appointments = pd.DataFrame(appointments)
    appointments.rename(columns=columns, inplace=True)

    # removed canceled appointments
    mask = ~appointments['Titre'].str.contains('annulé')
    appointments = appointments.loc[mask]

    # add record numbers to appointments
    appointments = appointments.set_index('RecordID').join(records)

    display_cols = ['Numéro', 'Date', 'Heure', 'Titre']
    st.dataframe(appointments[display_cols].reset_index(drop=False), hide_index=True)

    st.write((f'Found {len(appointments)} appointments and {sum(~mask)} canceled over last {nb_days} days!'))

    # reindex the DataFrame
    INDEX_COLS = ['RecordID', 'Date']
    appointments.reset_index(drop=False, inplace=True)
    appointments.sort_values(INDEX_COLS, inplace=True)
    appointments.set_index(INDEX_COLS, inplace=True)

    return appointments
