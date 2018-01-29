#!/bin/bash

timeout=$1

echo acquired lock
sleep $timeout
echo slept $timeout seconds
