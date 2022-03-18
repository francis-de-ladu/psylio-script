from datetime import datetime, timedelta

import pandas as pd


def get_appointments(session, records_df):
    end = datetime.now()
    start = end - timedelta(days=30)

    endpoint = f'https://admin.psylio.com/appointments/agenda/calendar?start={start.date()}&end={end.date()}'
    resp = session.get(endpoint)

    columns = {
        'startDate': 'Date',
        'startHour': 'Heure début',
        'endHour': 'Heure fin',
    }

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

    return appoints_df
