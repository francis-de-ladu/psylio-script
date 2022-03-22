import inspect
import logging
import os
import re
import subprocess
import time

import pandas as pd
import psutil

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
        full_path = os.path.join(os.getcwd(), unpaid_path)
        p = subprocess.Popen(
            f'start excel {full_path}', stdout=subprocess.PIPE, shell=True)

        while True:
            time.sleep(1)
            if "EXCEL.EXE" not in (p.name() for p in psutil.process_iter()):
                break
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
    newly_paid_df.fillna('', inplace=True)

    newly_paid_df['Type paiement'] = ''
    for i, invoice in newly_paid_df.iterrows():
        type_paiement = 'debit_transfer' if invoice['Interac'] else 'cash'
        newly_paid_df.loc[i, 'Type paiement'] = type_paiement

    return newly_paid_df
