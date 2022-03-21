import json
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def login(email, password, base_url='https://admin.psylio.com'):
    session = requests.Session()
    resp = session.get(base_url)

    soup = BeautifulSoup(resp.content, 'html.parser')
    _token = soup.find('input', {'name': '_token'}).get('value')

    payload = {
        '_token': _token,
        'login': {
            'email': email,
            'password': password,
            'account': 'ca',
        },
    }

    session.headers.update({
        'Content-Type': 'application/json',
    })

    logger.info('Attempting login...')
    resp = session.post(f'{base_url}/login', data=json.dumps(payload))
    soup = BeautifulSoup(resp.content, 'html.parser')
    alert = soup.find('div', {'class': 'alert alert-danger'})
    if alert:
        logger.info('Invalid username or password.')
        return

    update_headers(session)
    logger.info('Login successful!')
    return session


def update_headers(session):
    session.headers.update({
        'Origin': 'https://admin.psylio.com',
        'Referer': 'https://admin.psylio.com/assistance-requests',
        'Sec-Fetch-Site': 'same-origin',
        'X-Requested-With': 'XMLHttpRequest',
        'Access-Control-Allow-Origin': 'https://admin.psylio.com',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'X-Requested-With',
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64)'
                       ' AppleWebKit/537.36 (KHTML, like Gecko)'
                       ' Chrome/99.0.4844.51 Safari/537.36'),
        'Sec-CH-UA': ('" Not A;Brand";v="99",'
                      ' "Chromium";v="99",'
                      ' "Google Chrome";v="99"'),
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Linux"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    })
