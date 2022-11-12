import logging
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


def display_unpaid_invoices(records, invoices, unpaid_path):
    directory = os.path.dirname(unpaid_path)
    os.makedirs(directory, exist_ok=True)

    invoices = invoices.join(records, on='RecordID')
    invoices.reset_index(inplace=True, drop=False)
    invoices['Client(s)'] = invoices.apply(lambda inv: ' et '.join(filter(bool, inv[['Client 1', 'Client 2']])), axis=1)

    with st.form("paid_invoices"):
        st.markdown(
            """
            <style>
            [data-testid=column]:nth-of-type(n) [data-testid=stVerticalBlock]{
                gap: 0rem;
            }
            [data-testid=column]:nth-of-type(2n+1) [data-testid=stVerticalBlock]{
                bg-color: lightgrey;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        cols = st.columns([3, 2, 5, 6, 3])
        titles = ['Facture', 'Date', 'Client(s)', 'Mode de paiment', 'Date de paiment']
        for col, title in zip(cols, titles):
            col.markdown(f"**{title}**")

        payment_options = ('Non payé', 'Comptant', 'Interac')
        for idx, inv in invoices.iterrows():
            cols = st.columns([3, 2, 5, 6, 3])
            cols[0].write(inv['Facture'])
            cols[1].write(inv['Date'])
            cols[2].write(inv['Client(s)'])
            invoices.loc[idx, 'Mode paiement'] = \
                cols[3].radio(
                    "Mode de paiement",
                    payment_options,
                    key=f"mode_{inv['Facture']}",
                    horizontal=True,
                    label_visibility='collapsed',
            )
            invoices.loc[idx, 'Date paiement'] = \
                cols[4].date_input(
                    "Date de paiement",
                    min_value=datetime.strptime(inv['Date'], "%Y-%m-%d"),
                    max_value=date.today(),
                    key=f"date_{inv['Facture']}",
                    label_visibility='collapsed',
            )

        nb_cols = 7
        columns = st.columns(nb_cols)
        submitted = columns[nb_cols // 2].form_submit_button("Marquer payées")

    if submitted:
        newly_paid_invoices = invoices.loc[invoices['Mode paiement'] != "Non payé"]
        return newly_paid_invoices
    else:
        return invoices.iloc[:0]


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
