#!/bin/bash

export PYTHONPATH=/code:$PYTHONPATH
export BBOX_PORT_RANGE=30000-30001

export BBOX_BIND_IP=`python get_local_ip.py`

rm -rf  ~/.bbox
bbox init --home true

exec bbox "${BBOX_CMD}"
