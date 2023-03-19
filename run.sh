#!/bin/bash

HEADLESS=${1:-true}

streamlit run main.py --server.headless $HEADLESS
