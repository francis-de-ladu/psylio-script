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


def records_url(is_archived=False):
    return endpoint_url(REQUEST_URL, 'archive' if is_archived else '')


def appointments_url(nb_days):
    start, end = get_date_range(nb_days)
    query_params = dict(start=start, end=end)

    segments = ['appointments', 'agenda', 'calendar']
    return endpoint_url(PSYLIO_URL, *segments, **query_params)


def open_invoices_url(nb_days):
    start, end = get_date_range(nb_days)
    query_params = dict(start=start, end=end, date_type='manual')
    return endpoint_url(PSYLIO_URL, 'invoices', **query_params)


def record_url(record_id):
    return endpoint_url(REQUEST_URL, record_id)


def profile_url(record_id):
    return endpoint_url(record_url(record_id), 'profile')


def invoice_url(record_id, invoice_id=None, create=False):
    assert bool(invoice_id) ^ bool(create), f"`invoice_id` and `create` are mutually exclusive"
    suffix = 'create' if create else invoice_id
    return endpoint_url(record_url(record_id), 'invoices', suffix)


def record_invoices_url(record_id, state=None):
    query_params = {}
    if state is not None:
        assert state in ('paid', 'canceled')
        query_params['state'] = state

    return endpoint_url(record_url(record_id), 'invoices', **query_params)


def invoice_create_url(record_id):
    return endpoint_url(record_invoices_url(record_id), 'create')
