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

    tmp_dir = 'psylio-tmp'
    filename = 'unpaid.csv'
    unpaid_path = os.path.join(tmp_dir, filename)

    try:
        records_df = get_records(session)
        appoints_df = get_appointments(session, records_df)
        invoices_df = retrieve_invoices(session, records_df)

        create_missing_invoices(session, appoints_df, invoices_df)
        unpaid_df = get_unpaid_invoices(session)

        write_unpaid_to_file(records_df, unpaid_df, unpaid_path)
        newly_paid_df = get_newly_paid(unpaid_path)

        close_paid_invoices(email, password, unpaid_df, newly_paid_df)
        logging.info('Script completed successfully!')
        input("Press Enter to exit...")
    finally:
        if os.path.isfile(unpaid_path):
            os.remove(unpaid_path)
            os.rmdir(tmp_dir)


if __name__ == '__main__':
    main()
