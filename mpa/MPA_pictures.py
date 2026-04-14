"""
Python script to detect MPA-cars from pictures.

MPA_pictures.py v1.0

TODO:
- Verbeteren false positives: extra controle door vergelijking met echte ANPR bar
- website ap (lokaal): index.html -> keuze tussen "hotspot" en "dashboard cam"

"""

import cv2
import numpy as np
from ultralytics import YOLO
import sys
import os
import shutil
import platform
import argparse
import time
import requests
from datetime import datetime, time as dt_time
from time import gmtime, localtime, strftime, sleep
import json
from astral import LocationInfo
from astral.sun import sun
import zoneinfo
from pathlib import Path
import torch

torch.set_num_threads(2)
start_time = time.time()

# ================== CONFIG ==================
IMAGE_DIR = Path("/dev/shm/mjpeg")
DETECTED_DIR = Path("/hdd/mpa/detected")
PATTERN = "cam6*.jpg"
SLEEP_BETWEEN_CHECKS = 0.020         # 20 ms → ruim sneller dan 10 fps
SERVER_URL = "https://geert.zapto.org/mpa/mpa_upload.php"
API_KEY="Nr049axxJS8RaelrgoBgkl3B"
# ===========================================

# ================== REFERENTIE CONFIG ==================
REF_IMAGE_PATH = IMAGE_DIR / "ref.jpg"
REF_UPDATE_INTERVAL = 60.0          # seconden (elke minuut proberen)
SSIM_THRESHOLD = 1.05               # startwaarde, lager = toleranter, hoger = strenger
ROI_MARGIN = 30                     # pixels rand weglaten

# Globale variabelen voor referentie
ref_gray_roi = None                 # grijze ROI van huidige referentie (in memory)
last_ref_update_time = 0.0
# ================== AUTOTELLER ==================
daily_car_count = 0
daily_mpa_count = 0
no_car_streak = 0          # aantal opeenvolgende frames ZONDER auto in ROI
MIN_GAP_FRAMES = 2         # pas dit aan als je strenger/milder wilt
# ===============================================
# FPS meting
fps_start_time = 0.0
fps_frame_count = 0
current_fps = 0.0          # <--- dit is de variabele die je straks kunt gebruiken
# ================== STATISTICS & UPLOAD ==================
last_stats_upload_time = time.time()
last_stats_upload_frame = 0
STATS_UPLOAD_INTERVAL = 45.0      # minimum seconden tussen uploads (anti-spam)
MIN_FRAMES_BETWEEN_UPLOADS = 150  # minimum aantal frames tussen uploads (~15-25 sec)
# ========================================================

LOGDIR = "/hdd/mpa/"
LOGFILE = "MPA_pictures.log"

area_points = None
imageCtr = 0
first_frame = None
frame = None
ref_frame_roof_donker = None
ref_frame_roof_licht = None

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(DETECTED_DIR, exist_ok=True)

system = platform.system()
if system == "Windows":
  model = YOLO("yolo11n.onnx", task="detect")
else:
  model = YOLO("yolo11n_ncnn_model", task="detect")


########################################################################
#                                                                      #
#       main                                                           #
#                                                                      #
########################################################################
def main():
  global firstTime, out, cap
  global max1, max2
  global ref_gray_roi, last_ref_update_time
  global area_points, imageCtr, frame, first_frame
  global daily_car_count, daily_mpa_count, no_car_streak
  global current_fps, fps_frame_count
  global last_stats_upload_time, last_stats_upload_frame
  global ref_frame_roof_donker, ref_frame_roof_licht


  last_stats_upload_time = time.time()

  logger(f"MPA_pictures.py started.")
  # Initialiseer FPS meting
  fps_start_time = time.time()
  fps_frame_count = 0
  current_fps = 0.0

  # Gebruik polygoon uit het hulpprogramma.
  #area_points = np.array([[265, 142], [317, 140], [530, 241], [315, 262], [265, 142]], np.int32)
  #area_points = np.array([[234, 168], [300, 158], [446, 235], [375, 256], [258, 267], [235, 169]], np.int32)
  # --- ROI INLADEN ---
  CONFIG_FILE = "roi_config.json"

  try:
    with open(CONFIG_FILE, "r") as f:
      loaded_points = json.load(f)
    area_points = np.array(loaded_points, np.int32)
    logger(f"ROI succesvol ingeladen vanuit {CONFIG_FILE}")
  except Exception as e:
    # Fallback voor als het bestand niet bestaat of corrupt is
    logger(f"FOUT: Kon {CONFIG_FILE} niet laden. Gebruik standaard waarden. Error: {e}")
    area_points = np.array([[234, 168], [300, 158], [446, 235], [375, 256], [258, 267], [235, 169]], np.int32)

  ref_frame_roof_donker = cv2.imread("MPA_roof_donker.jpg", cv2.IMREAD_GRAYSCALE)
  ref_frame_roof_licht = cv2.imread("MPA_roof_licht.jpg", cv2.IMREAD_GRAYSCALE)

  if ref_frame_roof_donker is not None: logger("Ref donker jpg geladen.")
  if ref_frame_roof_licht is not None: logger("Ref licht jpg geladen.")

  detector = LightConditionDetector(51.22, 4.40)
  last_processed_key = None            # (bestandsnaam, mtime_ns)

  # Initialiseer referentie systeem
  ref_gray_roi = None
  last_ref_update_time = time.time()
  is_working_hours = True
  previous_is_working_hours = False

  while True:
    is_working_hours = is_allowed_time()
    if is_working_hours != previous_is_working_hours:
      if is_working_hours:
        logger("changed from sleep to working hours")
        # Reset teller bij begin van nieuwe bedrijfsdag
        daily_car_count = 0
        daily_mpa_count = 0
        no_car_streak = 0
        fps_frame_count = 0
        last_stats_upload_time = time.time() - 500
        last_stats_upload_frame = 0
        time.sleep(5)
        imageCtr = 0
      else:
        logger("changed from working hours to sleep")
      previous_is_working_hours = is_working_hours
      try_upload_statistics()
    if not is_working_hours: continue
    if os.path.exists("/home/domoticz/mpa.off"): continue

    ref_ready = IMAGE_DIR / "ref_ready"
    if os.path.exists(ref_ready):
      load_reference()
      ref_ready.unlink()

    # Alle relevante bestanden ophalen.
    files = list(IMAGE_DIR.glob(PATTERN))

    if len(files) < 2:
      print("Te weinig bestanden, wacht...")
      time.sleep(0.1)
      continue

    # Haal stats op met nanoseconde-precisie.
    file_stats = []
    for f in files:
      stat = f.stat()
      file_stats.append((stat.st_mtime_ns, f))   # tuple voor sorteren

    # Sorteer op mtime DESC → nieuwste eerst
    file_stats.sort(reverse=True)

    # Tweede jongste = index 1
    selected_mtime_ns, selected_path = file_stats[1]

    # Unieke sleutel voor dit exacte moment van dit bestand
    current_key = (str(selected_path), selected_mtime_ns)

    # Als het exact hetzelfde is als vorige keer → niet opnieuw verwerken
    if current_key == last_processed_key:
      time.sleep(SLEEP_BETWEEN_CHECKS)
      continue

    # === VERWERK ===
    #print(f"[{time.strftime('%H:%M:%S.%f')[:-3]}] "
    #      f"Verwerken 2de jongste: {selected_path.name} "
    #      f"(mtime_ns = {selected_mtime_ns})")
    if (imageCtr % 60 == 0): cond = detector.get_condition()
    #if (imageCtr % 100 == 0 and imageCtr > 0):
    #  logger(f"--100 img mark--")
    if (imageCtr % 100 == 0 and imageCtr > 0):
      # Bereken actuele FPS
      elapsed = time.time() - fps_start_time
      if elapsed > 0:
        current_fps = fps_frame_count / elapsed

      logger(f"--100 img mark--  FPS: {current_fps:.2f}  (elapsed: {elapsed:.1f}s)")

      # Reset voor volgende meting
      fps_start_time = time.time()
      fps_frame_count = 0

    #if (imageCtr % 600 == 0): load_reference()

    car_in_roi_this_frame = processImage(str(selected_path), cond)
    update_car_counter(car_in_roi_this_frame)

    # Update laatste verwerkte sleutel
    last_processed_key = current_key

    # === Probeer stats te uploaden zodra een auto net de ROI verlaten heeft ===
    if no_car_streak == 2:          # net overgeschakeld naar "geen auto meer"
      try_upload_statistics()

    # Heartbeat: upload stats als te lang geleden
    if time.time() - last_stats_upload_time > 180:
      try_upload_statistics()

    imageCtr += 1
    fps_frame_count += 1
    # Kleine pauze zodat we niet 100% CPU vreten
    time.sleep(SLEEP_BETWEEN_CHECKS)

########################################################################
#                                                                      #
#       load_reference                                                 #
#                                                                      #
########################################################################
def load_reference():
  global first_frame

  maxTry = 0
  while True:
    try:
      maxTry += 1
      if maxTry > 4: break
      first_frame = cv2.imread("/dev/shm/mjpeg/reference.jpg")
      logger("referentie geladen")
      break
    except e:
      logger(f"exception refframe: {e}")
      time.sleep(0.1)

########################################################################
#                                                                      #
#       processImage                                                   #
#                                                                      #
########################################################################
def processImage(filenameImage, cond):
  global frame, first_frame, ref_gray_roi, last_ref_update_time

  """
  frame = cv2.imread(filenameImage)
  if frame is None:
    logger(f"FOUT: Kon {filenameImage} niet lezen")
    return
  height, width = frame.shape[:2]

  # ROI: hele beeld minus 30px rand (tijdsbalk is weg)
  x1, y1 = ROI_MARGIN, ROI_MARGIN
  x2, y2 = width - ROI_MARGIN, height - ROI_MARGIN
  current_roi = frame[y1:y2, x1:x2]
  current_gray = cv2.cvtColor(current_roi, cv2.COLOR_BGR2GRAY)

  now = time.time()

  # === EERSTE KEER: ref.jpg aanmaken ===
  if ref_gray_roi is None:
    cv2.imwrite(str(REF_IMAGE_PATH), frame)
    logger(f"Eerste referentie aangemaakt: {REF_IMAGE_PATH.name}")

    ref_frame = cv2.imread(str(REF_IMAGE_PATH))
    if ref_frame is None:
      logger("FOUT: Kon ref.jpg niet laden na aanmaken")
      ref_gray_roi = current_gray.copy()
      last_ref_update_time = now
      return

    ref_roi = ref_frame[y1:y2, x1:x2]
    ref_gray_roi = cv2.cvtColor(ref_roi, cv2.COLOR_BGR2GRAY)
    last_ref_update_time = now
    logger(f"Referentie geladen (grootte ROI: {ref_gray_roi.shape})")
    return

  # === NORMALE VERWERKING: check of we een nieuwe ref kunnen maken ===
  time_since_update = now - last_ref_update_time

  if time_since_update >= REF_UPDATE_INTERVAL:
    # SSIM berekenen tussen huidige ROI en referentie ROI
    ssim_score = compute_ssim(ref_gray_roi, current_gray)

    if ssim_score >= SSIM_THRESHOLD:
      # Goed genoeg → nieuwe referentie opslaan
      cv2.imwrite(str(REF_IMAGE_PATH), frame)
      ref_gray_roi = current_gray.copy()
      last_ref_update_time = now
      logger(f"NIEUWE REFERENTIE opgeslagen! SSIM = {ssim_score:.4f} | Bestand: {filenameImage}")
    else:
      logger(f"Ref update OVERGESLAGEN - te veel verschil (SSIM = {ssim_score:.4f})")
  """
  # Detect MPA
  car_in_roi = detectMPA(filenameImage, cond)

  return car_in_roi

########################################################################
#                                                                      #
#       detectMPA                                                      #
#                                                                      #
########################################################################
def detectMPA(filenameImage, cond):
  global frame, first_frame, imageCtr, daily_mpa_count

  car_present_this_frame = False
  frame = cv2.imread(filenameImage)
  car_in_roi_this_frame = False

  #results = model(frame, stream=True, verbose=False)
  results = model(frame, classes=[2], verbose=False)[0]
  for box in results.boxes:
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    cx, cy = int((x1 + x2) / 2), int(y2)
    categorie = model.names[int(box.cls[0])]
    if categorie != 'car': continue
    car_conf = float(box.conf[0])
    car_height = y2 - y1
    car_width = x2 - x1

    if first_frame is None: break
    if car_conf < 0.5 or car_height < 80: continue   # skip dure berekeningen

    inside = cv2.pointPolygonTest(area_points, (cx, cy), False)
    if inside < 0: continue

    hit_counter = 0

    auto_roi = frame[y1:y2, x1:x2]
    if auto_roi.size == 0: continue

    # 1. Bepaal de zone direct boven de auto (bijv. 20 pixels hoog)
    roof_height = int(car_height * 0.13)
    roof_gapheight = int(roof_height * 0.2)
    roof_y1 = y1 - roof_height - roof_gapheight
    roof_y2 = y1 - roof_gapheight

    margin_left = int(car_width * 0.2)
    margin_right = int(car_width * 0.33)
    roof_x1 = x1 + margin_left
    roof_x2 = x2 - margin_right

    car_aspect = car_width / car_height
    car_in_roi_this_frame = True   # We hebben een auto in de ROI!

    #cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    #cv2.putText(frame, f"car {car_width}x{car_height} c:{car_conf:.2f}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Snij de nieuwe, kleinere ROI uit.
    roof_roi = frame[roof_y1:roof_y2, roof_x1:roof_x2]
    if roof_roi is None or roof_roi.size == 0: continue
    roof_roi2 = frame[roof_y1 - 15 : roof_y2 + 5, roof_x1 - 20 : roof_x2 + 20].copy()

    # Snij ook uit in het basisframe.
    first_roof_roi = first_frame[roof_y1:roof_y2, roof_x1:roof_x2]

    # Trek het contrast van beide beelden maximaal uit
    drive_gray = cv2.cvtColor(roof_roi, cv2.COLOR_BGR2GRAY)
    ref_gray = cv2.cvtColor(first_roof_roi, cv2.COLOR_BGR2GRAY)

    drive_equ = cv2.equalizeHist(drive_gray)
    ref_equ = cv2.equalizeHist(ref_gray)

    # Doe nu pas de vergelijking
    delta_roof = cv2.absdiff(drive_equ, ref_equ)

    # Drempelwaarde (Threshold): pixels die maar een klein beetje verschillen
    # (bijv. door ruis) worden 0 (zwart), de rest wordt 255 (wit).
    _, thresh = cv2.threshold(delta_roof, 25, 255, cv2.THRESH_BINARY)

    # Bereken het percentage witte pixels.
    non_zero_count = np.count_nonzero(thresh)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    percentage_diff = (non_zero_count / total_pixels) * 100

    # Nu gaan we allerlei metingen doen op de roof_roi.

    # Definieer de grenzen voor 'zuiver wit' (Let op: OpenCV gebruikt BGR, niet RGB!)
    lower_white = np.array([250, 250, 250]) # B, G, R
    upper_white = np.array([255, 255, 255])

    # Maak een masker: pixels binnen de range worden 255, de rest 0
    white_mask = cv2.inRange(roof_roi, lower_white, upper_white)

    # Tel het aantal witte pixels
    white_pixel_count = cv2.countNonZero(white_mask)
    total_pixels = roof_roi.shape[0] * roof_roi.shape[1]
    white_percentage = int((white_pixel_count / total_pixels) * 100)

    # Converteer de roof_roi naar HSV.
    hsv_roof = cv2.cvtColor(roof_roi, cv2.COLOR_BGR2HSV)

    # Bereken het gemiddelde van het tweede kanaal (index 1 = Saturation)
    mean_hsv = cv2.mean(hsv_roof)
    avg_saturation = int(mean_hsv[1])

    # Omzetten naar grijswaarden om lichtheid te meten
    gray_roof = cv2.cvtColor(roof_roi, cv2.COLOR_BGR2GRAY)

    # Bereken het gemiddelde van de helderste pixels
    # We kijken of er een significant 'licht' blok bovenop staat
    avg_brightness = np.mean(gray_roof)

    if avg_brightness <= 100: continue

    mean, std_dev = cv2.meanStdDev(roof_roi)

    # A smaller std_dev means higher homogeneity.
    homogeneity = int(std_dev[0][0])

    aspect_within_limits = False
    if car_aspect < 1.85 and car_aspect > 0.9: aspect_within_limits = True

    decision = (
      percentage_diff >= 69 and
        car_height > 90 and
        car_conf > 0.66 and
        x1 > 100 and
        aspect_within_limits
    )
    if cond == "donker":
      decision = (
        percentage_diff > 65 and
          car_height > 92 and
          car_conf > 0.5 and
          x1 > 100 and
          white_percentage >= 1 and
          white_percentage < 100 and
          aspect_within_limits
      )

    mpa_roof_confidence = None
    if decision:
      mpa_roof_confidence = calculate_roof_confidence(roof_roi2, cond)
      #if mpa_roof_confidence is not None and mpa_roof_confidence < 0.5: decision = False

    if decision:
      hit_counter += 1
    else:
      hit_counter = 0

    logger(
      f"roof:x{roof_x1} y{roof_y1} height:{car_height} wh:{white_percentage} "
      f"homog:{homogeneity} sat:{avg_saturation} decision:{decision}{hit_counter} "
      f"aspect:{car_aspect:.2f} conf:{car_conf:.2f} diff:{percentage_diff:.1f} "
      f"cond:{cond} count:{daily_car_count}"
    )

    if decision:
      logger(f"MPA car detected! conf:{mpa_roof_confidence}")
      daily_mpa_count += 1

      # Add some debug info to the frame.
      cv2.rectangle(frame, (x1, y1), (x2, y2), (155, 255, 0), 2)
      cv2.putText(frame, f"car {car_width}x{car_height} c:{car_conf:.2f}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (155, 255, 0), 2)

      # EXTRA DEBUGINFO ####
      # --- Bepaal positie voor extra debug info, linksonder in het frame.
      # We nemen 30 pixels marge van de onderkant en de zijkant
      text_x = 20
      text_y = int(frame.shape[0]) - 30

      # De tekst die we gaan tonen
      coord_text = f"X:{x1} Y:{y1} aspect:{car_aspect:.2f}"

      # Teken de tekst op het frame (in het groen: (0, 255, 0))
      cv2.putText(frame, coord_text, (text_x, text_y),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

      mpa_rc = "?"
      if mpa_roof_confidence is not None: mpa_rc = f"{mpa_roof_confidence:.2f}"

      cv2.putText(frame, f"MPA w:{white_percentage} h:{homogeneity} s:{avg_saturation} r:{percentage_diff:.1f} c:{mpa_rc}", (x1, roof_y1 - 5),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 0), 2)
      cv2.rectangle(frame, (roof_x1, roof_y1), (roof_x2, roof_y2), (255, 100, 0), 2)

      # Write frame in detected folder.
      tstamp = datetime.now().strftime('%Y%m%d_%H%M%S')
      mpaDetectedFilename = DETECTED_DIR / f"mpacar_{tstamp}.jpg"
      cv2.imwrite(str(mpaDetectedFilename), frame)
      # Write ref frame in detected folder.
      mpaDetectedRefFilename = DETECTED_DIR / f"mpacar_{tstamp}.ref.jpg"
      cv2.imwrite(str(mpaDetectedRefFilename), first_frame)

      upload_file(str(mpaDetectedFilename), 'photo')
      cleanupDetected()

      if notifications_enabled():
        notifyDetected(f"mpacar_{tstamp}")
      else:
        logger("Meldingen staan uit op server → geen notificatie verstuurd")

      videoFile = findVideo(tstamp)
      mpaDetectedVideoFilename = DETECTED_DIR / f"mpacar_{tstamp}.mp4"
      if videoFile:
        shutil.copy2(videoFile, mpaDetectedVideoFilename) # bewaar video
        upload_file(str(mpaDetectedVideoFilename), 'video')
      time.sleep(15)

      break

  return car_in_roi_this_frame

########################################################################
#                                                                      #
#       is_allowed_time                                                #
#                                                                      #
########################################################################
def is_allowed_time():
  now = datetime.now().time()
  return dt_time(9, 0) <= now <= dt_time(23, 59)

########################################################################
#                                                                      #
#       calculate_roof_confidence                                      #
#                                                                      #
########################################################################
def calculate_roof_confidence(uitsnede, conditie):
  ref = ref_frame_roof_licht if conditie == "licht" else ref_frame_roof_donker

  if ref is None or uitsnede is None: return None

  try:
    uitsnede_gray = to_gray(uitsnede)
    ref_gray = to_gray(ref)

    res = cv2.matchTemplate(uitsnede_gray, ref_gray, cv2.TM_CCOEFF_NORMED)

    _, max_val, _, _ = cv2.minMaxLoc(res)

    return max_val

  except Exception as e:
    print(f"Match fout: {e}")
    return 0.0

def to_gray(img):
  if img is None: return None

  # Case 1: puur grayscale (h, w)
  if len(img.shape) == 2: return img

  # Case 2: (h, w, 1) → squeeze naar (h, w)
  if len(img.shape) == 3 and img.shape[2] == 1: return img[:, :, 0]

  # Case 3: (h, w, 3) → echte kleur
  if len(img.shape) == 3 and img.shape[2] == 3: return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

  # fallback (zeldzaam)
  return img

########################################################################
#                                                                      #
#       cleanupDetected                                                #
#                                                                      #
########################################################################
def cleanupDetected():
  # huidige tijd (in seconden sinds epoch)
  now = time.time()

  # 2 dagen in seconden
  two_days = 2 * 24 * 60 * 60

  for file in DETECTED_DIR.iterdir():
    if file.is_file():
      file_mtime = file.stat().st_mtime
      if now - file_mtime > two_days: file.unlink()

########################################################################
#                                                                      #
#       notifyDetected                                                 #
#                                                                      #
########################################################################
def notifyDetected(ref):
  # Variabelen
  TOPIC = "mpa_b2a8f3e1-7c92-4d5a-af81-eb72910c4d32"
  SECRET_TOKEN = "slmqkdjfKDkem788934KKKLkllksdfm"

  # De URL voor de terugkoppeling.
  action_url = f"https://geert.zapto.org/mpa/actie_ntfy.php?token={SECRET_TOKEN}&ref={ref}"

  """
  curl -d "MPA auto gedetecteerd" \
       -H "Actions: view, Open site, https://geert.zapto.org/mpa/actie_ntfy.php?token=$SECRET_TOKEN&ref=$REF" \
       ntfy.sh/$TOPIC
  """

  # Verstuur de melding.
  response = requests.post(
    f"https://ntfy.sh/{TOPIC}",
    data="MPA auto gedetecteerd".encode('utf-8'),
    headers={
      "Title": "Voertuig Detectie",
      "Priority": "high",
      "Tags": "car,warning",
      "Actions": f"view, Open site, {action_url}"
    }
  )

  if response.status_code == 200:
    logger("Melding succesvol verzonden!")
  else:
    logger(f"Fout bij verzenden: {response.status_code}")

  return

########################################################################
#                                                                      #
#       notifications_enabled                                          #
#                                                                      #
########################################################################
def notifications_enabled() -> bool:
  """Check via API of meldingen aan staan op de server"""
  payload = {
    "type": "check_meldingen",
    "token": API_KEY
  }

  try:
    response = requests.post(SERVER_URL, data=payload, timeout=6)

    if response.status_code == 200:
      result = response.json()
      return result.get('meldingen_aan', False)
    else:
      logger(f"❌ Check meldingen mislukt: HTTP {response.status_code}")
      return False

  except Exception as e:
    logger(f"❌ Check meldingen error: {e}")
    return False

########################################################################
#                                                                      #
#       findVideo                                                      #
#                                                                      #
########################################################################
def findVideo(tstamp):
  ref_time = datetime.strptime(tstamp, "%Y%m%d_%H%M%S")

  timeout = 200  # x minuten
  interval = 5   # 5 seconden
  start_time = time.time()

  while True:
    candidates_after = []
    candidates_before = []

    for filename in os.listdir("/tmp"):
      if filename.endswith(".mp4.ready") and filename.startswith("motion_"):
        try:
          ts_part = filename[len("motion_"):-len(".mp4.ready")]
          file_time = datetime.strptime(ts_part, "%Y%m%d_%H%M%S")
        except ValueError:
          continue

        full_path = os.path.join("/tmp", filename)

        if file_time >= ref_time:
          candidates_after.append((file_time, full_path))
        else:
          candidates_before.append((file_time, full_path))

    # 1. Voorkeur: eerste NA of gelijk aan timestamp
    if candidates_after:
        candidates_after.sort()
        return candidates_after[0][1][:-6]

    # 2. Fallback: dichtstbijzijnde VOOR timestamp (max 10 sec bv)
    if candidates_before:
      candidates_before.sort(reverse=True)  # dichtstbijzijnde eerst
      closest_before_time, closest_before_file = candidates_before[0]

      delta = (ref_time - closest_before_time).total_seconds()

      if delta <= 10:  # tolerantie in seconden (aanpasbaar)
        return closest_before_file[:-6]

    # Timeout check
    if time.time() - start_time > timeout:
      return ""

    time.sleep(interval)

########################################################################
#                                                                      #
#       compute_ssim                                                   #
#                                                                      #
########################################################################
def compute_ssim(img1, img2):
  """Berekent SSIM tussen twee grijze afbeeldingen (pure OpenCV + numpy)"""
  C1 = (0.01 * 255) ** 2
  C2 = (0.03 * 255) ** 2

  mu1 = cv2.GaussianBlur(img1, (11, 11), 1.5)
  mu2 = cv2.GaussianBlur(img2, (11, 11), 1.5)

  mu1_sq = mu1 * mu1
  mu2_sq = mu2 * mu2
  mu12 = mu1 * mu2

  sigma1_sq = cv2.GaussianBlur(img1 * img1, (11, 11), 1.5) - mu1_sq
  sigma2_sq = cv2.GaussianBlur(img2 * img2, (11, 11), 1.5) - mu2_sq
  sigma12 = cv2.GaussianBlur(img1 * img2, (11, 11), 1.5) - mu12

  ssim_map = ((2 * mu12 + C1) * (2 * sigma12 + C2)) / \
             ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

  return float(cv2.mean(ssim_map)[0])

########################################################################
#                                                                      #
#       upload_file                                                    #
#                                                                      #
########################################################################
def upload_file(file_path: str, file_type: str):
  """Upload foto of video naar de thuisserver"""
  if not os.path.exists(file_path):
    logger(f"Bestand niet gevonden: {file_path}")
    return False

  try:
    with open(file_path, 'rb') as f:
      files = {'file': f}
      data = {
        'token': API_KEY,
        'type': file_type   # 'photo' of 'video'
      }

      response = requests.post(
        SERVER_URL,
        files=files,
        data=data,
        timeout=30          # 30 seconden timeout
      )

    if response.status_code == 200:
      result = response.json()
      logger(f"✅ Upload succesvol: {result.get('filename')}")
      return True
    else:
      logger(f"❌ Upload mislukt: {response.status_code} - {response.text}")
      return False

  except requests.exceptions.RequestException as e:
    logger(f"❌ Verbindingsfout: {e}")
    return False

########################################################################
#                                                                      #
#       try_upload_statistics                                          #
#                                                                      #
########################################################################
def try_upload_statistics():
  """Probeer statistieken te uploaden op rustige momenten"""
  global last_stats_upload_time, last_stats_upload_frame

  # Tijd-gebaseerde check
  now = time.time()
  if now - last_stats_upload_time < STATS_UPLOAD_INTERVAL:
    #logger(f"try_upload_statistics: too soon {now} {last_stats_upload_time}")
    return False

  # Frame-gebaseerde check
  if last_stats_upload_frame > 0 and (imageCtr - last_stats_upload_frame) < MIN_FRAMES_BETWEEN_UPLOADS:
    #logger(f"try_upload_statistics: Too soon {last_stats_upload_frame} {imageCtr}")
    return False

  payload = {
    "type":  "stats",
    "token": API_KEY,
    "daily_car_count": daily_car_count,
    "daily_mpa_count": daily_mpa_count,
    "current_fps": round(current_fps, 2),
    "imageCtr": imageCtr
  }

  try:
    response = requests.post(
      SERVER_URL,
      data=payload,
      timeout=8                      # kortere timeout zodat het niet te lang blokkeert
    )

    if response.status_code == 200:
      logger(f"📊 Stats geüpload → cars:{daily_car_count} mpa:{daily_mpa_count} fps:{current_fps:.1f}")
      last_stats_upload_time = now
      last_stats_upload_frame = imageCtr   # onthoud frame nummer
      return True
    else:
      logger(f"Stats upload HTTP {response.status_code}")

  except requests.exceptions.RequestException as e:
    logger(f"Stats upload timeout/netwerkfout: {e}")
  except Exception as e:
    logger(f"Stats upload onverwachte fout: {e}")

  return False

########################################################################
#                                                                      #
#       update_car_counter                                             #
#                                                                      #
########################################################################
def update_car_counter(car_present: bool):
  """Update de dagelijkse autoteller met debouncing"""
  global daily_car_count, no_car_streak

  #logger(f"inside update_car_counter:car_present:{car_present} no_car_streak:{no_car_streak}")
  if car_present:
    # Auto aanwezig → als er genoeg gap was → nieuwe auto!
    if no_car_streak >= MIN_GAP_FRAMES:
      daily_car_count += 1
      logger(f"🚗 NIEUWE AUTO geteld! Totaal vandaag: {daily_car_count}")
    no_car_streak = 0
  else:
    # Geen auto → streak verhogen
    no_car_streak += 1

########################################################################
#                                                                      #
#       logger                                                         #
#                                                                      #
########################################################################
def logger(s):
  try:
    logsize = os.path.getsize(LOGDIR + LOGFILE)
    if (logsize > 10000000):
      os.remove(LOGDIR + LOGFILE)
  except:
    print("logfile could not be removed or does not exist")

  now2 = strftime("%Y/%m/%d_%H:%M:%S", localtime())
  with open(LOGDIR + LOGFILE, "a") as LOG:
    LOG.write("%s %s\n" % (now2, s) )
    LOG.close()

  print("%s %s" % (now2, s) )

########################################################################
#                                                                      #
#       LightConditionDetector                                         #
#                                                                      #
########################################################################
class LightConditionDetector:
  def __init__(self, lat, lon, timezone="Europe/Brussels"):
    self.location = LocationInfo(
      name="custom",
      region="",
      timezone=timezone,
      latitude=lat,
      longitude=lon
    )
    self.tz = zoneinfo.ZoneInfo(timezone)
    self._cache_date = None
    self._sun = None
  def _update_sun_times(self):
    today = datetime.now(self.tz).date()
    if today != self._cache_date:
      self._sun = sun(self.location.observer, date=today, tzinfo=self.tz)
      self._cache_date = today
  def get_condition(self):
    self._update_sun_times()
    now = datetime.now(self.tz)
    if self._sun["sunrise"] <= now <= self._sun["sunset"]:
      return "licht"
    if self._sun["dawn"] <= now < self._sun["sunrise"]:
      return "schemer"
    if self._sun["sunset"] < now <= self._sun["dusk"]:
      return "schemer"
    return "donker"


########################################################################
#                                                                      #
#       Start main function.                                           #
#                                                                      #
########################################################################
main()
