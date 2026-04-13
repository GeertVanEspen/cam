# cam - Camera Scripts

Deze repository bevat alle scripts en tools die gebruikt worden voor de camera-systemen.

Het centrale onderdeel is **`camDashboard.py`**: een Python-applicatie voor real-time camerabewaking met motion detection.

## Hoofdscript: camDashboard.py

### Functies
- **Real-time RTSP streaming** van de camera
- **Motion detection** met instelbare gevoeligheid
- **Pre-record buffer** (meerdere seconden opnemen vóór de beweging)
- **Automatische opname** van motion clips met cooldown
- **Inject mode**: mogelijkheid om MP4-bestanden in te voegen (bijv. testvideo's of externe opnames) die automatisch worden afgespeeld op 10 fps
- **Live MJPEG output** → `cam6a.jpg`, `cam6b.jpg`, ... voor webdashboard
- **Automatische opslag**: MP4's worden lokaal gemaakt, gekopieerd naar NFS-share én naar OneDrive (via rclone)

### Belangrijke kenmerken
- Alles draait grotendeels in RAM (`/dev/shm`) voor maximale snelheid

## Andere bestanden in deze repo

- **`camDashboard.sh`** → start/stop en monitoring script

## Installatie & Gebruik

### Vereisten
- Python 3 met `opencv-python`, `requests`
- `ffmpeg`
- `rclone` (geconfigureerd met OneDrive remote)
- Toegang tot een NFS-share (`/nfsshare/raspinas/...`)
- RTSP-stream van de camera

### Basisconfiguratie
Pas de configuratie in `camDashboard_config_private.py` aan:
- `RTSP_URL`
- `STORAGE_DIR`, `INJECT_DIR`, `CLOUD_REMOTE`

### Starten
```bash
./camDashboard.sh
