import os

import pandas as pd


def write_unpaid_to_file(records_df, unpaid_df, filename='unpaid.csv'):
    unpaid_df['paymentDate'] = ''
    unpaid_df['debit_transfer'] = ''
    unpaid_df['cash'] = ''

    unpaid_df = unpaid_df.join(records_df, on='record_id')
    unpaid_df.reset_index(inplace=True)

    columns = ['Facture', 'Date', 'Numéro de dossier',
               'Client 1', 'Client 2', 'Service(s)', 'Montant dû']
    to_file_df = unpaid_df[columns].sort_values('Date')

    to_file_df.set_index(['Facture', 'Date'], inplace=True)
    to_file_df[['Date paiement', 'Comptant', 'Interac']] = ''
    to_file_df.to_csv(filename)

    if os.name == 'nt':
        os.startfile(filename).read()
    else:
        os.popen(f'libreoffice --calc {filename}').read()


def get_newly_paid(with_paid_df, filename):
    with_paid_df = pd.read_csv(filename)
    with_paid_df['Date paiement'] = pd.to_datetime(
        with_paid_df['Date paiement'])
    with_paid_df

    has_date = with_paid_df['Date paiement'].notna()
    is_cash = with_paid_df['Comptant'].notna()
    is_debit = with_paid_df['Interac'].notna()

    to_mark = has_date & (is_cash ^ is_debit)
    to_drop = ~(has_date | is_cash | is_debit)
    invalid = ~(to_mark ^ to_drop)

    assert not any(invalid), 'Inconsistent values have been found!'

    newly_paid_df = with_paid_df.loc[with_paid_df['Date paiement'].notna()]

    with pd.option_context('mode.chained_assignment', None):
        for col in ['Comptant', 'Interac']:
            if newly_paid_df[col].dtype in ('object', 'string'):
                newly_paid_df[col] = newly_paid_df[col].str.strip()

    return newly_paid_df
