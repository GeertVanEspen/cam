#!/bin/bash

export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin


sleep 3
cd /hdd/mpa
while true; do
  ./venv/bin/python /hdd/mpa/MPA_pictures.py
  sleep 10
done


exit 0

