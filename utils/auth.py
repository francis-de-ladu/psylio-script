import json

import requests
from bs4 import BeautifulSoup


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
        # 'origin': 'https://admin.psylio.com',
    })

    resp = session.post(f'{base_url}/login', data=json.dumps(payload))
    assert resp.status_code == 200, 'Login failed :('

    return session
