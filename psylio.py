import pandas as pd
from utils.appointments import get_appointments
from utils.auth import login
from utils.invoices import (close_paid_invoices, create_missing_invoices,
                            get_invoices, get_unpaid_invoices)
from utils.io import get_newly_paid, write_unpaid_to_file
from utils.records import get_records


def main():
    email = '<email>'
    password = <password >

    print('Attempting login...', end=' ')
    session = login(email, password)
    print('Login successful!')

    # set headers
    session.headers.update({
        'Origin': 'https://admin.psylio.com',
        'Referer': 'https://admin.psylio.com/assistance-requests',
        'Sec-Fetch-Site': 'same-origin',
        'X-Requested-With': 'XMLHttpRequest',

        'Access-Control-Allow-Origin': 'https://admin.psylio.com',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'X-Requested-With',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36',


        'Sec-CH-UA': '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Linux"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    })

    records_df = get_records(session)
    appoints_df = get_appointments(session, records_df)
    invoices_df = get_invoices(session, records_df)

    create_missing_invoices(session, appoints_df, invoices_df)
    unpaid_df = get_unpaid_invoices(session)

    filename = 'unpaid.csv'
    write_unpaid_to_file(records_df, unpaid_df, filename)

    with_paid_df = pd.read_csv(filename)
    newly_paid_df = get_newly_paid(with_paid_df, filename)

    unpaid_df.set_index('Facture', inplace=True)
    newly_paid_df.set_index('Facture', inplace=True)

    close_paid_invoices(email, password, unpaid_df, newly_paid_df)


if __name__ == '__main__':
    main()
