#!/bin/bash

export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

while [ 1 ]
do
  #php /cam/cam3proxy.php
  /cam/mjpegStreamSplitter -l /root/streamcam3.log -s "http://raspberry12:8080/101/mjpg/stream" -o "/dev/shm/mjpeg/cam3"
  sleep 15
done
