import inspect
import logging
import os
import re

import pandas as pd

logger = logging.getLogger(__name__)


def write_unpaid_to_file(records_df, unpaid_df, unpaid_path):
    directory = os.path.dirname(unpaid_path)
    os.makedirs(directory, exist_ok=True)

    unpaid_df = unpaid_df.join(records_df, on='record_id')
    unpaid_df.reset_index(inplace=True)

    columns = ['Facture', 'Date', 'Numéro de dossier',
               'Client 1', 'Client 2', 'Service(s)', 'Montant dû']
    unpaid_df = unpaid_df[columns].sort_values('Date')

    unpaid_df.set_index(['Facture', 'Date'], inplace=True)
    unpaid_df[['Date paiement', 'Comptant', 'Interac']] = ''
    unpaid_df.to_csv(unpaid_path)

    if os.name == 'nt':
        #dirname = os.path.dirname(os.path.abspath(inspect.stack()[0][1]))
        dirname = os.path.dirname(__file__)
        full_path = os.path.join(dirname, unpaid_path)
        os.startfile(full_path).read()
    else:
        os.popen(f'libreoffice --calc {unpaid_path}').read()


def get_newly_paid(unpaid_path):
    with_paid_df = pd.read_csv(unpaid_path)

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
