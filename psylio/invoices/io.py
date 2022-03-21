import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


def write_unpaid_to_file(records_df, unpaid_df, filename, tmp_dir='./tmp'):
    unpaid_df = unpaid_df.join(records_df, on='record_id')
    unpaid_df.reset_index(inplace=True)

    columns = ['Facture', 'Date', 'Numéro de dossier',
               'Client 1', 'Client 2', 'Service(s)', 'Montant dû']
    unpaid_df = unpaid_df[columns].sort_values('Date')

    unpaid_df.set_index(['Facture', 'Date'], inplace=True)
    unpaid_df[['Date paiement', 'Comptant', 'Interac']] = ''

    os.makedirs(tmp_dir, exist_ok=True)
    path = f'{tmp_dir}/{filename}'
    unpaid_df.to_csv(path)

    if os.name == 'nt':
        os.startfile(path).read()
    else:
        os.popen(f'libreoffice --calc {path}').read()


def get_newly_paid(filename, tmp_dir='./tmp'):
    path = f'{tmp_dir}/{filename}'
    with_paid_df = pd.read_csv(path)

    with_paid_df['Date paiement'] = pd.to_datetime(
        with_paid_df['Date paiement'])

    has_date = with_paid_df['Date paiement'].notna()
    is_cash = with_paid_df['Comptant'].notna()
    is_debit = with_paid_df['Interac'].notna()

    was_paid = has_date & (is_cash ^ is_debit)
    not_paid = ~(has_date | is_cash | is_debit)
    valid = was_paid ^ not_paid

    assert all(valid), 'Inconsistent values have been found!'

    newly_paid_df = with_paid_df.loc[with_paid_df['Date paiement'].notna()]

    with pd.option_context('mode.chained_assignment', None):
        for col in ['Comptant', 'Interac']:
            if newly_paid_df[col].dtype == 'object':
                newly_paid_df[col] = newly_paid_df[col].str.strip()

    return newly_paid_df
