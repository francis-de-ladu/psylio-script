import logging
from functools import reduce
from operator import getitem

import pandas as pd

from ..routes import appointments_url

logger = logging.getLogger(__name__)


def retrieve_appointments(session, nb_days=30):
    columns = dict(
        startDate='Date',
        startHour='Heure',
        assistanceRequest__data__id='RecordID',
        title='Titre',
    )

    logger.info('Getting appointments...')
    resp = session.get(appointments_url(nb_days))

    # retrieve appointments from response
    appointments = []
    for entry in resp.json():
        data = entry['modal']['appointment']
        infos = {key: reduce(getitem, key.split('__'), data) for key in columns}
        appointments.append(infos)

    # convert to a DataFrame and rename the columns
    appointments = pd.DataFrame(appointments)
    appointments.rename(columns=columns, inplace=True)

    # reindex the DataFrame
    INDEX_COLS = ['RecordID', 'Date']
    appointments.sort_values(INDEX_COLS, inplace=True)
    appointments.set_index(INDEX_COLS, inplace=True)

    # removed cancelled appointments
    mask = ~appointments['Titre'].str.contains('annulé')
    appointments = appointments.loc[mask]

    logger.info((f'Found {len(appointments)} appointments and {sum(~mask)} cancelled over last {nb_days} days!'))

    return appointments
