import time
from datetime import date, timedelta

import streamlit as st
import streamlit.components.v1 as components
from st_btn_select import st_btn_select
from streamlit_modal import Modal


def get_date_range(days):
    end = date.today()
    start = end - timedelta(days=days)
    return start, end


def request_confirm(content, key):
    placeholder = st.empty()
    with placeholder.container():
        for type_, value in content:
            getattr(st, type_)(value)

        selection = st_btn_select(("Accept", "Cancel", "Exit"), index=1, key=key)

        while selection == "Cancel":
            time.sleep(.1)

        if selection == "Exit":
            st.write("Exiting application...")
            exit()
        else:
            placeholder.empty()


def request_confirm2(content, key):
    placeholder = st.empty()
    with placeholder.container():
        for type_, value in content:
            getattr(st, type_)(value)

        selection = st_btn_select(("Accept", "Cancel", "Exit"), index=1, key=key)

        while selection == "Cancel":
            time.sleep(.1)

        if selection == "Exit":
            st.write("Exiting application...")
            exit()
        else:
            placeholder.empty()

    # answer = input(f'>>> {msg} (y/n): ')
    # if not answer.lower().startswith('y'):
    #     print('Exiting script...')
    #     time.sleep(5)
    #     exit(1)
