from urllib.parse import urlencode
from ..utils import get_date_range

PSYLIO_URL = 'https://admin.psylio.com'
REQUEST_URL = PSYLIO_URL + '/assistance-requests'


def endpoint_url(*segments, **query_params):
    endpoint = '/'.join(seg.strip('/') for seg in segments)
    if query_params:
        endpoint += '?' + urlencode(query_params)
    return endpoint


def base_url():
    return PSYLIO_URL


def login_url():
    return endpoint_url(PSYLIO_URL, 'login')


def records_url(archive=False):
    return endpoint_url(REQUEST_URL, 'archive' if archive else '')


def appointments_url(nb_days):
    start, end = get_date_range(nb_days)
    query_params = dict(start=start, end=end)

    segments = ['appointments', 'agenda', 'calendar']
    return endpoint_url(PSYLIO_URL, *segments, **query_params)


def open_invoices_url(nb_days):
    start, end = get_date_range(nb_days)
    query_params = dict(start=start, end=end, date_type='manual')
    return endpoint_url(PSYLIO_URL, 'invoices', **query_params)


def profile_url(record_id):
    return endpoint_url(REQUEST_URL, record_id)


def invoice_url(record_id, invoice_id):
    record_url = profile_url(record_id)
    return endpoint_url(record_url, 'invoices', invoice_id)


def record_invoices_url(record_id, state='open'):
    record_url = profile_url(record_id)
    return endpoint_url(record_url, 'invoices', state=state)
