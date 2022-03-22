import time


def request_confirm(msg):
    answer = input(f'>>> {msg} (y/n): ')
    if not answer.lower().startswith('y'):
        print('Exiting script...')
        time.sleep(5)
        exit(1)
