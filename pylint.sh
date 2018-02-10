#!/bin/bash
type pylint >/dev/null 2>&1 || { echo >&2 "pylint not installed. use pip install pylint."; exit 1;}
pylint --rcfile=./pylintrc $(find . -name '*.py') 2>&1 | tee /tmp/pylint.txt
if [ -s /tmp/pylint.txt ]; then
    exit 1
else
    exit 0
fi
