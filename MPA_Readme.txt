MPA inspecteur installatie
==========================

Windows Server 2025
-------------------
mkdir c:\cam
cd \cam

python -m venv venv
.\venv\Scripts\Activate

pip install astral
pip install ultralytics opencv-python-headless
pip install opencv-python

copy <pCloud>:data/allen/insteon/cam -> c:/cam
copy /cam/index.php /inetpub/wwwroot/ntfy/




