import getpass
import logging
import os

from psylio.appointments import get_appointments
from psylio.auth import login
from psylio.invoices import (close_paid_invoices, create_missing_invoices,
                             get_newly_paid, get_unpaid_invoices,
                             retrieve_invoices, write_unpaid_to_file)
from psylio.records import get_records


def main():
    fmt = '[{asctime}] [{levelname}]  {message}'
    formatter = logging.Formatter(fmt, style='{', datefmt='%Y-%m-%d %H:%M:%S')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(handlers=[handler], level=logging.DEBUG)
    for lib in ('urllib3', 'selenium'):
        logging.getLogger(lib).setLevel(logging.WARNING)

    os.environ['WDM_LOG_LEVEL'] = str(logging.WARNING)

    session = None
    while session is None:
        email = input('Username: ')
        password = getpass.getpass('Password: ')
        session = login(email, password)

    try:
        records_df = get_records(session)
        appoints_df = get_appointments(session, records_df)
        invoices_df = retrieve_invoices(session, records_df)

        create_missing_invoices(session, appoints_df, invoices_df)
        unpaid_df = get_unpaid_invoices(session)

        filename = 'unpaid.csv'
        write_unpaid_to_file(records_df, unpaid_df, filename)
        newly_paid_df = get_newly_paid(filename)

        close_paid_invoices(email, password, unpaid_df, newly_paid_df)
    finally:
        path = f'./tmp/{filename}'
        if os.path.isfile(path):
            os.remove(path)


if __name__ == '__main__':
    main()
