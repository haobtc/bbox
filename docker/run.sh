#!/bin/bash

export PYTHONPATH=/code:$PYTHONPATH
export BBOX_PORT_RANGE=30000-30001

rm -rf  ~/.bbox
bbox init --home true

exec bbox "${BBOX_CMD}"
