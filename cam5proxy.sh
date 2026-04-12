export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

while [ 1 ]
do
  /cam/mjpegStreamSplitter -l /root/streamcam5.log -s "http://portablecam:8080/101/mjpg/stream" -o "/dev/shm/mjpeg/cam5"
  sleep 15
done

#while [ 1 ]
#do
#  php /cam/cam5proxy.php
#  sleep 5
#done
