import time
from urllib.parse import urlencode, urljoin


def request_confirm(msg):
    answer = input(f'>>> {msg} (y/n): ')
    if not answer.lower().startswith('y'):
        print('Exiting script...')
        time.sleep(5)
        exit(1)


def get_endpoint_url(*segments, **query_params):
    path = '/'.join(seg.strip('/') for seg in segments)
    endpoint = urljoin('https://admin.psylio.com/', path)
    if query_params:
        endpoint += '?' + urlencode(query_params)
    return endpoint
