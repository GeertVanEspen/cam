import cv2
import time
from datetime import datetime
import os
import subprocess
import shutil
from collections import deque

# ===================== CONFIG =====================
OUTPUT_DIR = "/dev/shm/mjpeg"
CAM_NBR = 4
CAM_NAME = ""
PRE_RECORD_SECONDS = 5
FPS_ESTIMATE       = 10               # schatting van je substream
PRE_BUFFER_SIZE    = int(PRE_RECORD_SECONDS * FPS_ESTIMATE)   # ≈ 50
DEBUG = False

if CAM_NBR == 1:
  CAM_NAME = "frontdoor"
if CAM_NBR == 4:
  CAM_NAME = "frontwindow"

RTSP_URL = f"rtsp://admin:Whoo1124@{CAM_NAME}:554/h264Preview_01_sub"

# === MOTION CONFIG (pas aan naar wens) ===
MOTION_THRESHOLD = 1000           # aantal veranderde pixels → tune dit!
MOTION_COOLDOWN_SECONDS = 10      # hoe lang na laatste beweging nog doorgaan met opnemen
CLIPS_RAM_DIR = f"/dev/shm/motion_clips{CAM_NBR}"   # tijdelijke opslag (RAM = bliksemsnel)
STORAGE_DIR = f"/media/usb/cam/Reo_{CAM_NAME}"  # hier komen de uiteindelijke MP4's

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CLIPS_RAM_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)

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

while True:
  ret, frame = cap.read()
  if not ret:
    if DEBUG: print("Frame drop → herstart poging")
    cap.release()
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
    time.sleep(1)
    pre_buffer.clear()          # buffer leeg bij reconnect
    continue

  h, w = frame.shape[:2]   # 360, 640
  crop_w = int(h * 4 / 3)  # 480
  # rechts behouden (links weg)
  frame = frame[:, w - crop_w : w]

  # nu resizen naar 640x480
  #frame = cv2.resize(frame, (640, 480))

  # BELANGRIJK: altijd in de buffer stoppen (ook als er geen motion is)
  pre_buffer.append(frame.copy())   # .copy() belangrijk!

  # === Live-weergave ===
  path = f"{OUTPUT_DIR}/cam{CAM_NBR}{letter}.jpg"
  pathBusy = f"{OUTPUT_DIR}/cam{CAM_NBR}{letter}.busy"
  open(pathBusy, "w").write("busy")
  cv2.imwrite(path, frame)
  os.remove(pathBusy)
  letter = chr((ord(letter) - ord('a') + 1) % 4 + ord('a'))

  # ===================== MOTION DETECTION & RECORDING =====================
  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  gray = cv2.resize(gray, (320, 180))          # klein = supersnel

  if prev_gray is not None:
    frame_delta = cv2.absdiff(gray, prev_gray)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    motion_pixels = cv2.countNonZero(thresh)

    current_time = time.time()

    if motion_pixels > MOTION_THRESHOLD:
      if not recording:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clip_dir = os.path.join(CLIPS_RAM_DIR, timestamp)
        os.makedirs(clip_dir, exist_ok=True)
        frame_num = 0

        # === Pre-buffer wegschrijven (de 5 seconden ervoor) ===
        if DEBUG: print(f"🚨 MOTION → start opname {timestamp}  (incl {len(pre_buffer)} pre-frames)")
        for i, pre_frame in enumerate(pre_buffer):
          pre_path = os.path.join(clip_dir, f"frame{frame_num:06d}.jpg")
          cv2.imwrite(pre_path, pre_frame)
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

      # cooldown voorbij? → stoppen en MP4 maken
      if current_time - last_motion_time > MOTION_COOLDOWN_SECONDS:
        recording = False
        output_mp4 = os.path.join(STORAGE_DIR, f"motion_{timestamp}.mp4")

        if DEBUG: print(f"Opname gestopt → ffmpeg ({frame_num} frames, incl pre-record)")
        try:
          subprocess.run([
            "ffmpeg", "-framerate", str(FPS_ESTIMATE),
            "-i", os.path.join(clip_dir, "frame%06d.jpg"),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-movflags", "+faststart",                       # direct afspeelbaar in browser
            "-vf", "setpts=PTS-STARTPTS",  # zorgt dat timing klopt
            output_mp4
          ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)

          if DEBUG: print(f"✅ Clip klaar: {output_mp4}")
        except Exception as e:
          if DEBUG: print("FFmpeg fout:", e)

        # opruimen (RAM vrijhouden)
        try:
          shutil.rmtree(clip_dir)
        except:
          pass

  prev_gray = gray.copy()
