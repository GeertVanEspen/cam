"""
Python script to detect MPA-cars from pictures.

TODO:
- reference sneller ophalen via signaal in /dev/shm
- Onedrive herstellen bij vastlopen in powerscript: continue lus maken
- SMS arduino aanroepen vanuit actie_ntfy.php
- knop "herstart inspecteur": boodschap "restarting" blijft -> javascript

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
# ======================================================

LOGDIR = "/hdd/mpa/"
LOGFILE = "MPA_pictures.log"

area_points = None
imageCtr = 0
first_frame = None
frame = None

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

  logger(f"MPA_pictures.py started.")

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


  detector = LightConditionDetector(51.22, 4.40)
  last_processed_key = None            # (bestandsnaam, mtime_ns)

  # Initialiseer referentie systeem
  ref_gray_roi = None
  last_ref_update_time = time.time()

  while True:
    if not is_allowed_time():
      time.sleep(5)
      imageCtr = 0
      continue
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
    if (imageCtr % 100 == 0 and imageCtr > 0):
      logger(f"--100 img mark--")
    if (imageCtr % 600 == 0): load_reference()

    processImage(str(selected_path), cond)

    # Update laatste verwerkte sleutel
    last_processed_key = current_key
    imageCtr += 1
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
  detectMPA(filenameImage, cond)

########################################################################
#                                                                      #
#       detectMPA                                                      #
#                                                                      #
########################################################################
def detectMPA(filenameImage, cond):
  global frame, first_frame, imageCtr

  frame = cv2.imread(filenameImage)

  #results = model(frame, stream=True, verbose=False)
  results = model(frame, classes=[2], verbose=False)[0]
  #for r in results:
  #  for box in r.boxes:
  for box in results.boxes:
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    cx, cy = int((x1 + x2) / 2), int(y2)
    categorie = model.names[int(box.cls[0])]
    if categorie != 'car': continue
    car_conf = float(box.conf[0])
    car_height = y2 - y1
    car_width = x2 - x1

    if first_frame is None: return

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

    #cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    #cv2.putText(frame, f"car {car_width}x{car_height} c:{car_conf:.2f}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Snij de nieuwe, kleinere ROI uit.
    roof_roi = frame[roof_y1:roof_y2, roof_x1:roof_x2]

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
          aspect_within_limits
      )
    if decision:
      hit_counter += 1
    else:
      hit_counter = 0

    logger(
      f"roof:x{roof_x1} y{roof_y1} height:{car_height} wh:{white_percentage} "
      f"homog:{homogeneity} sat:{avg_saturation} decision:{decision}{hit_counter} "
      f"aspect:{car_aspect:.2f} conf:{car_conf:.2f} diff:{percentage_diff:.1f} cond:{cond}"
    )

    if decision:
      logger("MPA car detected!")

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

      cv2.putText(frame, f"MPA w:{white_percentage} h:{homogeneity} s:{avg_saturation} {percentage_diff:.1f}", (x1, roof_y1 - 5),
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
      notifyDetected(f"mpacar_{tstamp}")
      videoFile = findVideo(tstamp)
      mpaDetectedVideoFilename = DETECTED_DIR / f"mpacar_{tstamp}.mp4"
      if videoFile:
        shutil.copy2(videoFile, mpaDetectedVideoFilename) # bewaar video
        upload_file(str(mpaDetectedVideoFilename), 'video')
      time.sleep(15)

      return

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
#       findVideo                                                      #
#                                                                      #
########################################################################
def findVideo(tstamp):
  ref_time = datetime.strptime(tstamp, "%Y%m%d_%H%M%S")

  timeout = 300  # 5 minuten
  interval = 5   # 5 seconden
  start_time = time.time()

  while True:
    found_files = []

    for filename in os.listdir("/tmp"):
      if filename.endswith(".mp4.ready") and filename.startswith("motion_"):
        try:
          # Extract timestamp uit filename
          # motion_20260401_142940.mp4.ready
          ts_part = filename[len("motion_"):-len(".mp4.ready")]
          file_time = datetime.strptime(ts_part, "%Y%m%d_%H%M%S")
        except ValueError:
          continue  # skip bestanden met onverwacht formaat

        if file_time > ref_time:
          full_path = os.path.join("/tmp", filename)
          found_files.append((file_time, full_path))

    if found_files:
      # Sorteer op timestamp (oudste eerst)
      found_files.sort()
      ready_file = found_files[0][1]

      # Verwijder .ready extensie
      return ready_file[:-6]

    # Timeout check
    if time.time() - start_time > timeout: return ""

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
