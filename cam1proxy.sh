export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

while [ 1 ]
do
  php /cam/cam1proxy.php
  sleep 5
done
