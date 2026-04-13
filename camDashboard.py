# https://github.com/GeertVanEspen/cam

import cv2
import time
from datetime import datetime
import os
import subprocess
import shutil
from collections import deque
import requests
from requests.auth import HTTPBasicAuth
import logging
from pathlib import Path
import threading
from queue import Queue, Empty

# ===================== CONFIG =====================
LOGFILE = '/root/camDashboard.log'
CAM_NAME = "Giotti"
CAM_NBR = 6
OUTPUT_DIR = "/dev/shm/mjpeg"
STORAGE_DIR = f"/nfsshare/raspinas/cam/Reo_{CAM_NAME}"  # hier komen de uiteindelijke MP4's
UPLOAD_URL = "http://geert.zapto.org/insteon/cam/upload_image.php"
LOCAL_TEMP_DIR = "/tmp"   # hier ffmpegt hij lokaal (bliksemsnel, geen NFS)

PRE_RECORD_SECONDS = 3
FPS_ESTIMATE       = 10               # schatting van je substream
PRE_BUFFER_SIZE    = int(PRE_RECORD_SECONDS * FPS_ESTIMATE)   # ≈ 50
DEBUG = False

# Hoe vaak uploaden? (1 = elk frame, 5 = elke 5e frame ≈ 2 fps)
UPLOAD_EVERY_N_FRAMES = 1

# ===================== INJECT CONFIG =====================
INJECT_DIR = "/hdd/mpa/inject"   # of een ander pad op je SSD
INJECT_CHECK_INTERVAL = 5.0                    # seconden (alleen tijdens RTSP)
FPS_INJECT = 10.0                     # exacte FPS van de injected MP4's
FRAME_TIME_INJECT = 1.0 / FPS_INJECT  # ≈ 0.1 seconde per frame
last_frame_time = 0.0
just_injected = False

# Optioneel: opruimen oude inject bestanden (1x per uur)
CLEANUP_OLDER_THAN_DAYS = 1
last_cleanup_time = 0

# === MOTION CONFIG (pas aan naar wens) ===
MOTION_THRESHOLD = 1000           # aantal veranderde pixels → tune dit!
MOTION_COOLDOWN_SECONDS = 8       # hoe lang na laatste beweging nog doorgaan met opnemen
CLIPS_RAM_DIR = f"/dev/shm/motion_clips{CAM_NBR}"   # tijdelijke opslag (RAM = bliksemsnel)
STORAGE_DIR = f"/nfsshare/raspinas/cam/Reo_{CAM_NAME}"  # hier komen de uiteindelijke MP4's

# ===================== GEVOELIGE CONFIG (uit config_private.py) =====================
try:
  from camDashboard_config_private import RTSP_URL, USERNAME, PASSWORD, CLOUD_REMOTE
except ImportError:
  print("ERROR: config_private.py niet gevonden!")
  print("Maak een camDashboard_config_private.py bestand aan met je wachtwoorden.")
  exit(1)

# ===================== BACKGROUND ENCODING =====================
ENCODING_QUEUE = Queue(maxsize=5)   # max 5 taken in queue (veilig)

# Logging
logging.basicConfig(
  filename=LOGFILE,
  level=logging.INFO,
  format='%(asctime)s | %(levelname)s | %(message)s',
  datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("=== camDashboard.py gestart ===")

# === Inject mode variables ===
inject_mode = False
current_mp4_path = None
last_inject_check = 0.0

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CLIPS_RAM_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(INJECT_DIR, exist_ok=True)

# ===================== get_gateway_linux FUNCTIE ==========
def get_gateway_linux():
  # Voert 'ip route' uit en zoekt naar de 'default' regel
  cmd = "ip route | grep default"
  output = subprocess.check_output(cmd, shell=True).decode()
  return output.split()[2]

# ===================== UPLOAD FUNCTIE =====================
def upload_frame(frame_path):
  try:
    with open(frame_path, 'rb') as f:
      files = {'image': (os.path.basename(frame_path), f, 'image/jpeg')}
      response = requests.post(
        UPLOAD_URL,
        files=files,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        timeout=5  # voorkom hangen bij trage server
      )

    if response.status_code == 200:
      print(f"Upload OK: {frame_path} → {response.status_code}")
    else:
      print(f"Upload mislukt: {frame_path} → {response.status_code} - {response.text[:100]}")

  except Exception as e:
    print(f"Upload error: {e}")

# ===================== get_oldest_mp4 FUNCTIE =====================
def get_oldest_mp4(directory):
  """Geeft het oudste .mp4 bestand in de map, of None als er geen zijn."""
  try:
    files = [f for f in os.listdir(directory) if f.lower().endswith('.mp4')]
    if not files:
        return None
    # Sorteer op creatie-tijd (oudste eerst)
    files_with_time = [(f, os.path.getctime(os.path.join(directory, f))) for f in files]
    oldest = min(files_with_time, key=lambda x: x[1])
    return os.path.join(directory, oldest[0])
  except Exception as e:
    logging.error(f"Fout bij ophalen oudste MP4: {e}")
    return None

# ===================== cleanup_old_inject_files FUNCTIE =====================
def cleanup_old_inject_files():
  """Verwijdert mp4 bestanden ouder dan CLEANUP_OLDER_THAN_DAYS."""
  global last_cleanup_time
  try:
    now = time.time()
    if now - last_cleanup_time < 3600: return   # max 1x per uur
    last_cleanup_time = now

    cutoff = now - (CLEANUP_OLDER_THAN_DAYS * 86400)
    deleted = 0
    for f in os.listdir(INJECT_DIR):
      if not f.lower().endswith('.mp4'):
        continue
      path = os.path.join(INJECT_DIR, f)
      if os.path.getctime(path) < cutoff:
        try:
          os.unlink(path)
          deleted += 1
          logging.info(f"Oude inject file opgeruimd: {f}")
        except Exception as del_e:
          logging.warning(f"Kon oude file niet deleten {f}: {del_e}")
    if deleted > 0:
      logging.info(f"{deleted} oude inject bestanden opgeruimd")
  except Exception as e:
    logging.error(f"Cleanup fout: {e}")

# ===================== encoding_worker FUNCTIE =====================
def encoding_worker():
  """Worker thread die encodings één voor één afhandelt."""
  logging.info("Background encoding worker gestart")

  while True:
    try:
      # Haal taak uit queue (blokkeert tot er iets is)
      task = ENCODING_QUEUE.get()
      clip_dir, timestamp, frame_num, local_mp4, output_mp4 = task

      logging.info(f"🔨 Encoding gestart in background: motion_{timestamp}.mp4 ({frame_num} frames)")

      try:
        # === FFmpeg encoding (lokaal) ===
        subprocess.run([
          "ffmpeg", "-framerate", str(FPS_ESTIMATE),
          "-i", os.path.join(clip_dir, "frame%06d.jpg"),
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
          "-movflags", "+faststart",
          "-vf", "setpts=PTS-STARTPTS",
          local_mp4
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)

        # === Kopiëren naar NFS + rclone ===

        if os.path.exists(local_mp4) and "192.168.123" in get_gateway_linux():
          try:
            shutil.copy2(local_mp4, output_mp4)                    # → nfsshare
            subprocess.run(
              ["rclone", "copy", local_mp4, CLOUD_REMOTE],
              check=True, timeout=60,
              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logging.info(f"✅ MP4 gekopieerd naar NFS ({output_mp4}) én cloud ({CLOUD_REMOTE})")
          except Exception as copy_e:
            logging.error(f"⛔ Kopieer/upload fout: {type(copy_e).__name__} - {copy_e}")
          finally:
            try:
              # Alle oude motion_*.mp4 EN motion_*.mp4.ready in /tmp verwijderen (behalve deze .mp4).
              for old_file in os.listdir(LOCAL_TEMP_DIR):
                if old_file.startswith("motion_") and old_file.endswith((".mp4", ".mp4.ready")):
                  old_path = os.path.join(LOCAL_TEMP_DIR, old_file)
                  try:
                    file_mtime = os.path.getmtime(old_path)
                    # Alleen verwijderen als ouder dan 1 uur
                    if time.time() - file_mtime > 3600: os.unlink(old_path)
                  except Exception:
                    pass

              # .ready bestand aanmaken (zodat ander script het kan oppikken)
              ready_path = local_mp4 + ".ready"
              with open(ready_path, "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write(f"original: {output_mp4}\n")

              logging.info(f"✅ MP4 klaar in /tmp: {os.path.basename(local_mp4)} + .ready bestand")

            except:
              pass

      except subprocess.TimeoutExpired:
        logging.error("⛔ FFmpeg timeout in background thread")
      except Exception as e:
        logging.error(f"Encoding fout in background: {type(e).__name__} - {e}")
      finally:
        # Opruimen clip map in RAM
        try:
          shutil.rmtree(clip_dir)
        except:
          pass

        ENCODING_QUEUE.task_done()

    except Exception as outer_e:
      logging.error(f"Onverwachte fout in encoding worker: {outer_e}")


# ===================== MAIN LOOP =====================
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

if not cap.isOpened():
  print("Kan RTSP stream niet openen")
  exit(1)

frame_count = 0
letter = "a"

# === motion variables ===
prev_gray = None
recording = False
frame_num = 0
clip_dir = None
last_motion_time = 0
timestamp = ""

# Nieuwe ring buffer voor pre-record
pre_buffer = deque(maxlen=PRE_BUFFER_SIZE)   # houdt laatste ~5s frames vast

# Start background encoding thread
encoding_thread = threading.Thread(target=encoding_worker, daemon=True)
encoding_thread.start()
logging.info("Background encoding thread gestart (daemon)")

while True:
  # ===================== FRAME OPHALEN (RTSP of INJECT) =====================
  current_time = time.time()

  # Alleen checken op nieuwe inject files als we NIET in inject_mode zitten
  if not inject_mode and (current_time - last_inject_check > INJECT_CHECK_INTERVAL):
    last_inject_check = current_time
    cleanup_old_inject_files()          # optioneel opruimen

    oldest_mp4 = get_oldest_mp4(INJECT_DIR)
    if oldest_mp4:
      logging.info(f"🚀 Injectie gestart: {os.path.basename(oldest_mp4)}")
      if cap is not None and cap.isOpened(): cap.release()       # oude RTSP/cap loslaten
      cap = cv2.VideoCapture(oldest_mp4, cv2.CAP_FFMPEG)
      cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
      inject_mode = True
      current_mp4_path = oldest_mp4
      pre_buffer.clear()               # pre-buffer resetten bij bron-wissel
      last_frame_time = current_time   # timing reset
      just_injected = True             # ← belangrijk voor reference.jpg

  # Nu een frame lezen (van RTSP of van huidige MP4)
  ret, frame = cap.read()

  if not ret:
    if inject_mode:
      # MP4 is afgelopen (of corrupt/niet leesbaar)
      logging.info(f"✅ Injectie beëindigd: {os.path.basename(current_mp4_path or 'onbekend')}")
      try:
        if current_mp4_path and os.path.exists(current_mp4_path):
          os.unlink(current_mp4_path)
          logging.info(f"   → MP4 verwijderd: {current_mp4_path}")
      except Exception as del_e:
        logging.error(f"Kon inject MP4 niet deleten: {del_e}")

      # Terug naar RTSP
      inject_mode = False
      current_mp4_path = None
      just_injected = False

    else:
      # Normale RTSP frame drop
      if DEBUG: print("Frame drop → herstart poging")
      logging.warning("Frame drop → reconnect poging")

    # In beide gevallen: cap loslaten en nieuwe RTSP openen
    if cap is not None and cap.isOpened():
      cap.release()

    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

    time.sleep(1)
    pre_buffer.clear()
    just_injected = False
    continue

  # ===================== REFERENCE.JPG BIJ INJECTIE =====================
  if inject_mode and just_injected and frame is not None:
    try:
      reference_path = f"{OUTPUT_DIR}/reference.jpg"
      cv2.imwrite(reference_path, frame)
      Path('/dev/shm/mjpeg/ref_ready').touch()
      logging.info("Reference.jpg aangemaakt vanuit eerste frame van injectie")
    except Exception as ref_e:
      logging.error(f"Fout bij maken reference.jpg van injectie: {ref_e}")

    just_injected = False   # alleen de allereerste frame van de injectie

  # ---- FPS BEHEER TIJDENS INJECTIE ----
  if inject_mode:
    # Wacht tot het volgende frame volgens 10 fps mag komen
    elapsed = current_time - last_frame_time
    sleep_time = FRAME_TIME_INJECT - elapsed

    if sleep_time > 0: time.sleep(sleep_time)

    # Update timestamp voor volgend frame
    last_frame_time = time.time()   # gebruik actuele tijd na sleep
  # ================================= END BLOCK===============================


  h, w = frame.shape[:2]   # 360, 640
  crop_w = int(h * 4 / 3)  # 480
  # rechts behouden (links weg)
  # frame = frame[:, w - crop_w : w]

  # nu resizen naar 640x480
  #frame = cv2.resize(frame, (640, 480))

  # BELANGRIJK: altijd in de buffer stoppen (ook als er geen motion is)
  pre_buffer.append(frame.copy())   # .copy() belangrijk!

  # === Live-weergave ===
  path = f"{OUTPUT_DIR}/cam{CAM_NBR}{letter}.jpg"
  pathBusy = f"{OUTPUT_DIR}/cam{CAM_NBR}{letter}.busy"
  open(pathBusy, "w").write("busy")
  cv2.imwrite(path, frame)
  Path(pathBusy).unlink(missing_ok=True)
  logging.debug(f"Live jpg bijgewerkt: {path}")
  letter = chr((ord(letter) - ord('a') + 1) % 4 + ord('a'))

  # Upload als het tijd is
  #if frame_count % UPLOAD_EVERY_N_FRAMES == 0:
  #  print(f"→ Upload frame {ts} ...")
  #  upload_frame(path)

  # ===================== MOTION DETECTION & RECORDING =====================
  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  gray = cv2.resize(gray, (320, 180))          # klein = supersnel

  if prev_gray is not None:
    logging.debug("Motion detection gestart")
    frame_delta = cv2.absdiff(gray, prev_gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    motion_pixels = cv2.countNonZero(thresh)

    current_time = time.time()

    if motion_pixels > MOTION_THRESHOLD:
      if not recording:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.info(f"🚨 MOTION DETECTED → start opname {timestamp} (pre-buffer {len(pre_buffer)} frames)")
        clip_dir = os.path.join(CLIPS_RAM_DIR, timestamp)
        os.makedirs(clip_dir, exist_ok=True)

        frame_num = 0
        # === Pre-buffer wegschrijven (de 5 seconden ervoor) ===
        if DEBUG: print(f"🚨 MOTION → start opname {timestamp}  (incl {len(pre_buffer)} pre-frames)")
        for i, pre_frame in enumerate(pre_buffer):
          pre_path = os.path.join(clip_dir, f"frame{frame_num:06d}.jpg")
          cv2.imwrite(pre_path, pre_frame)
          ################### reference maken van eerste frame pre_record buffer bij beweging ####
          if frame_num == 0:
            shutil.copy2(pre_path, f"{OUTPUT_DIR}/reference.jpg")
            Path('/dev/shm/mjpeg/ref_ready').touch()
          ########################################################################################
          frame_num += 1

        recording = True
        if DEBUG: print(f"🚨 MOTION DETECTED → starten opname {timestamp}")
      last_motion_time = current_time

    # Als we aan het opnemen zijn → frame opslaan + cooldown check
    if recording:
      # Normale opname tijdens beweging
      clip_path = os.path.join(clip_dir, f"frame{frame_num:06d}.jpg")
      cv2.imwrite(clip_path, frame)          # full resolution voor het filmpje
      frame_num += 1





      if current_time - last_motion_time > MOTION_COOLDOWN_SECONDS:
        recording = False

        # Taak voorbereiden voor background thread.
        output_mp4 = os.path.join(STORAGE_DIR, f"motion_{timestamp}.mp4")
        local_mp4  = os.path.join(LOCAL_TEMP_DIR, f"motion_{timestamp}.mp4")

        # Taak in queue stoppen → main loop gaat meteen verder!
        try:
          ENCODING_QUEUE.put_nowait((clip_dir, timestamp, frame_num, local_mp4, output_mp4))
          logging.info(f"📤 Encoding taak in queue gezet: motion_{timestamp}.mp4 ({frame_num} frames)")
        except Exception as qe:
          logging.error(f"Kon encoding taak niet in queue zetten: {qe}")
          # Fallback: opruimen als queue vol is
          try:
            shutil.rmtree(clip_dir)
          except:
            pass
        #continue   # ← belangrijk: ga meteen terug naar main loop



      # cooldown voorbij? → stoppen en MP4 maken
      """
      if current_time - last_motion_time > MOTION_COOLDOWN_SECONDS:
        recording = False

        output_mp4 = os.path.join(STORAGE_DIR, f"motion_{timestamp}.mp4")
        local_mp4  = os.path.join(LOCAL_TEMP_DIR, f"motion_{timestamp}.mp4")

        logging.info(f"Cooldown voorbij → start FFmpeg LOKAAL ({frame_num} frames) naar {local_mp4}")

        if DEBUG: print(f"Opname gestopt → ffmpeg ({frame_num} frames, incl pre-record)")
        try:
          subprocess.run([
            "ffmpeg", "-framerate", str(FPS_ESTIMATE),
            "-i", os.path.join(clip_dir, "frame%06d.jpg"),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-movflags", "+faststart",
            "-vf", "setpts=PTS-STARTPTS",
            local_mp4                                      # ← nu lokaal!
          ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
          if DEBUG: print(f"✅ FFmpeg lokaal klaar: {local_mp4}")
        except subprocess.TimeoutExpired:
            logging.error("⛔ FFmpeg TIMEOUT na 90s → clip niet gemaakt")
        except Exception as e:
            logging.error(f"FFmpeg fout: {type(e).__name__} - {e}")

        # === Kopiëren naar NFS + rclone (OneDrive) ===
        if os.path.exists(local_mp4) and "192.168.123" in get_gateway_linux():
          try:
            shutil.copy2(local_mp4, output_mp4)                    # → nfsshare
            subprocess.run(
              ["rclone", "copy", local_mp4, CLOUD_REMOTE],
              check=True, timeout=60,
              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            logging.info(f"✅ MP4 gekopieerd naar NFS ({output_mp4}) én cloud ({CLOUD_REMOTE})")
          except Exception as copy_e:
            logging.error(f"⛔ Kopieer/upload fout: {type(copy_e).__name__} - {copy_e}")
          finally:
            try:
              # Alle oude motion_*.mp4 EN motion_*.mp4.ready in /tmp verwijderen (behalve deze .mp4).
              for old_file in os.listdir(LOCAL_TEMP_DIR):
                if old_file.startswith("motion_") and old_file.endswith((".mp4", ".mp4.ready")):
                  old_path = os.path.join(LOCAL_TEMP_DIR, old_file)
                  try:
                    file_mtime = os.path.getmtime(old_path)
                    # Alleen verwijderen als ouder dan 1 uur
                    if time.time() - file_mtime > 3600: os.unlink(old_path)
                  except Exception:
                    pass

              # .ready bestand aanmaken (zodat ander script het kan oppikken)
              ready_path = local_mp4 + ".ready"
              with open(ready_path, "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write(f"original: {output_mp4}\n")

              logging.info(f"✅ MP4 klaar in /tmp: {os.path.basename(local_mp4)} + .ready bestand")

            except:
              pass
        else:
          logging.warning("Geen lokaal MP4 beschikbaar (FFmpeg faalde)")

        # Opruimen (RAM vrijhouden)
        try:
          shutil.rmtree(clip_dir)
        except:
          pass
    """

  prev_gray = gray.copy()

  frame_count += 1

  if (frame_count % 1000 == 0):
    frame_count = 0
    if (os.path.getsize(LOGFILE) > 10000000): os.remove(LOGFILE)

  if frame_count % 50 == 0:
    logging.info(f"Framecount {frame_count}")
