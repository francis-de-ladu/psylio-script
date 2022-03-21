def request_confirm(msg):
    answer = input(f'>>> {msg} (y/n): ')
    if not answer.lower().startswith('y'):
        print('Exiting script...')
        exit(1)
