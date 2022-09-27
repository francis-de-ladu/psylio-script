import time

from datetime import date, timedelta


def get_date_range(days):
    end = date.today()
    start = end - timedelta(days=days)
    return start, end


def request_confirm(msg):
    answer = input(f'>>> {msg} (y/n): ')
    if not answer.lower().startswith('y'):
        print('Exiting script...')
        time.sleep(5)
        exit(1)
