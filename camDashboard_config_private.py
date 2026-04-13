"""
config_private.py
Gevoelige configuratie voor camDashboard.py
DIT BESTAND MAG NOOIT IN GITHUB KOMEN!
"""

# ===================== GEVOELIGE CONFIG =====================

# RTSP stream (bevat wachtwoord)
RTSP_URL = "rtsp://admin:Whoo1124@10.42.0.182:554/h264Preview_01_sub"

# Basic Auth voor de upload naar je webserver
USERNAME = "geert"
PASSWORD = "Brompt1124"

# rclone remote (OneDrive)
CLOUD_REMOTE = "onedrive:/cam/ReoMPA"

# Optioneel: andere gevoelige dingen die je later eventueel wilt toevoegen
# UPLOAD_URL = "http://geert.zapto.org/..."   # als je deze ook privé wilt houden
