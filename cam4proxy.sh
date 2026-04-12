export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

while [ 1 ]
do
  #php /cam/cam4proxy.php
  python /cam/camreo4proxy.py
  sleep 5
done
