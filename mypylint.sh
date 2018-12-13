#!/bin/sh

export MYPYPATH=./mypypath
if [ -z $1 ]; then
    pyfile=$(find aiobbox -name '*.py')
    echo $pyfile
    exec mypy "$pyfile"
else
    exec mypy $*
fi
