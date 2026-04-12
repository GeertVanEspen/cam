#!/bin/bash

export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin


# Zorg dat de map bestaat (in RAM)
mkdir -p /dev/shm/mjpeg
sleep 30
while true; do
  python /cam/camDashboard.py
  sleep 10
done


exit 0

# Below is deprecated
# Basis URL van de camera (pas wachtwoord en IP eventueel aan)
camUrl="http://10.42.0.182/cgi-bin/api.cgi?cmd=Snap&channel=0&user=admin&password=Whoo1124&width=640&height=480"

echo "Start snapshot loop - 60 seconden lang (ongeveer 1 fps)"
echo "Bestanden worden opgeslagen in: /dev/shm/mjpeg"

# Starttijd
start_time=$(date +%s)

while true; do
    # Huidige tijd met milliseconden
    timestamp=$(date +%Y%m%d_%H%M%S_%3N)

    # Bestandsnaam voorbeeld: 20260225_143712_847.jpg
    filename="/dev/shm/mjpeg/snap_${timestamp}.jpg"

    # Snapshot ophalen
    curl --silent --show-error -o "$filename" "$camUrl"

    # Optioneel: toon voortgang (commentarieer weg als je het niet wilt)
    # echo -n "."

    # Stop na 60 seconden
    current_time=$(date +%s)
    #if (( current_time - start_time >= 60 )); then
    #    break
    #fi

    # Wacht ~1 seconde (curl duurt zelf ook al wat tijd)
    #sleep 0.92
done

echo ""
echo "Klaar. ${start_time} → $(date +%s) seconden"
#ls -lh /dev/shm/mjpeg | tail -n 8   # toon laatste 8 bestanden ter controle
