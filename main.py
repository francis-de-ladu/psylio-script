import getpass
import logging
import os

import pandas as pd
import streamlit as st
from loguru import logger

from psylio.appointments import retrieve_appointments
from psylio.auth import login
from psylio.invoices import (close_paid_invoices, create_missing_invoices,
                             display_unpaid_invoices, retrieve_open_invoices,
                             retrieve_paid_invoices, retrieve_unpaid_invoices)
from psylio.records import get_record_infos_from_ids, retrieve_records

st.set_page_config(layout='wide')

st.markdown(
    """
    <style>
    [data-testid=column]:nth-of-type(n) [data-testid=stVerticalBlock] {
        gap: 0rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def my_print(something, desc=None):
    if desc:
        logger.info(''.join(['\n', desc, '\n']))
    logger.info(something)


def main():
    main_container = st.container()
    with main_container:
        # fmt = '[{asctime}] [{levelname}]  {message}'
        # formatter = logging.Formatter(fmt, style='{', datefmt='%Y-%m-%d %H:%M:%S')

        # handler = logging.StreamHandler()
        # handler.setFormatter(formatter)

        # logging.basicConfig(handlers=[handler], level=logging.INFO)
        for lib in ('urllib3', 'selenium'):
            logging.getLogger(lib).setLevel(logging.WARNING)

        os.environ['WDM_LOG_LEVEL'] = str(logging.WARNING)

        session = None
        while session is None:
            email = "fdl9044@gmail.com"  # input('Username: ')
            password = "ikatjcC62vC2!f5"  # getpass.getpass('Password: ')
            session = login(email, password)

        tmp_dir = 'psylio-tmp'
        filename = 'unpaid_invoices.csv'
        unpaid_path = os.path.join(tmp_dir, filename)

        try:
            # retrieve records
            records = retrieve_records(session)
            # my_print(records, "RECORDS")

            # retrieve recent appointments
            appointments = retrieve_appointments(session, records, 30)
            # my_print(appointments, "APPOINTS")

            # retrieve open invoices and match them with appointments
            open_invoices = retrieve_open_invoices(session)
            # my_print(appointments, "OPEN_INVOICES")
            if open_invoices is not None:
                # only keep appointments without invoice
                open_invoices = appointments.join(open_invoices).dropna()
                appointments.drop(open_invoices.index, inplace=True)

            # retrieve paid invoices and match them with appointments
            record_ids = appointments.index.unique(level=0).tolist()
            paid_invoices = retrieve_paid_invoices(session, record_ids)
            # my_print(paid_invoices, "PAID_INVOICES")
            paid_invoices = appointments.join(paid_invoices)
            paid_invoices = paid_invoices.loc[paid_invoices['État'] != 'Reçu envoyé']

            # group all invoices with unsent receipts together
            invoices = pd.concat([open_invoices, paid_invoices])
            # my_print(invoices, "ALL INVOICES")

            # extract invoices that must be created as well as associated record infos
            missing_invoices = invoices.loc[invoices['Facture'].isna()]
            record_ids = missing_invoices.index.unique(level=0).tolist()
            records = get_record_infos_from_ids(session, record_ids)
            # my_print(records)

            # add record infos to invoices to be created
            missing_invoices.reset_index(inplace=True, drop=False)
            missing_invoices.set_index('RecordID', inplace=True)
            missing_invoices = missing_invoices.join(records)
            # my_print(missing_invoices)

            # create invoices for appointments without one
            missing_invoices.where(pd.notnull(missing_invoices), None, inplace=True)
            create_missing_invoices(session, missing_invoices.iloc[:1])
            unpaid_invoices = retrieve_unpaid_invoices(session)
            # my_print(unpaid_invoices)

            # records = pd.DataFrame()  # retrieve_records(session)
            newly_paid_invoices = display_unpaid_invoices(records, unpaid_invoices, unpaid_path)

            if not newly_paid_invoices.empty:
                my_print(newly_paid_invoices)
                close_paid_invoices(email, password, unpaid_invoices, newly_paid_invoices)

                logger.info('Script completed successfully!')
                input("Press Enter to exit...")
        finally:
            if os.path.isfile(unpaid_path):
                os.remove(unpaid_path)
                os.rmdir(tmp_dir)


if __name__ == '__main__':
    main()
