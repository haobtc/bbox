#!/bin/bash

timeout=$1

echo `date +'%H:%M:%S'` acquired lock
sleep $timeout
echo `date +'%H:%M:%S'` slept $timeout seconds

