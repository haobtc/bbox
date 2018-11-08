#!/bin/sh

export MYPYPATH=mypy
exec mypy $*
