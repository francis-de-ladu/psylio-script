import logging
import os
import subprocess
import time
from datetime import date, datetime
import pandas as pd
import psutil
import streamlit as st

logger = logging.getLogger(__name__)

def set_payment_method(invoices, idx, *args, **kwargs):
    print("set_payment_method")
    pass

def set_payment_date(invoices, idx, *args, **kwargs):
    print("set_payment_date")
    pass


def mark_as_paid(invoices):
    print("mark_as_paid")
    print(invoices)

def write_unpaid_to_file(records, invoices, unpaid_path):
    directory = os.path.dirname(unpaid_path)
    os.makedirs(directory, exist_ok=True)

    invoices = invoices.join(records, on='RecordID')
    invoices.reset_index(inplace=True, drop=False)
    print(invoices.columns)
    print(invoices)
    invoices['Client'] = invoices.apply(lambda inv:' et '.join(filter(bool, inv[['Client 1', 'Client 2']])), axis=1)
    

    # columns = ['Facture', 'Date', 'Numéro de dossier',
    #            'Client 1', 'Client 2', 'Service(s)', 'Montant']
    # invoices = invoices[columns].sort_values('Date')

    # invoices.set_index(['Facture', 'Date'], inplace=True)
    display_cols = ['Facture', 'Date', 'Client']
    print(invoices[display_cols])
    # invoices[['Date paiement', 'Comptant', 'Interac']] = ''

    st.set_page_config(layout='wide')

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
            cols[2].write(inv['Client'])
            cols[3].radio(
                "Mode de paiement",
                payment_options,
                key=f"mode_{inv['Facture']}",
                on_change=set_payment_method(invoices, idx),
                horizontal=True,
                label_visibility='collapsed',
            )
            cols[4].date_input(
                "Date de paiement",
                min_value=datetime.strptime(inv['Date'], "%Y-%m-%d"),
                max_value=date.today(),
                key=f"date_{inv['Facture']}",
                on_change=set_payment_date(invoices, idx),
                label_visibility='collapsed',
            )

        nb_cols = 7
        columns = st.columns(nb_cols)
        submitted = columns[nb_cols // 2].form_submit_button(
            "Marquer payées",
            mark_as_paid(invoices),
        )

        if submitted:
            "submitted1"
            print(invoices)
            
    if submitted:
        "submitted2"
        print(invoices)

    time.sleep(1000)
    

    # # invoices.to_csv(unpaid_path)

    # if os.name == 'nt':
    #     full_path = os.path.join(os.getcwd(), unpaid_path)
    #     p = subprocess.Popen(
    #         f'start excel {full_path}', stdout=subprocess.PIPE, shell=True)

    #     while True:
    #         time.sleep(1)
    #         if "EXCEL.EXE" not in (p.name() for p in psutil.process_iter()):
    #             break
    # else:
    #     os.popen(f'libreoffice --calc {unpaid_path}').read()


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
