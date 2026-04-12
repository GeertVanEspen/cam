"""
Python script to detect MPA-cars from mp4 files.
Authors: Geert Van Espen and Gemini
Gemini user: desossa38.rpi1@gmail.com
Gemini pinned topic: Yolo en MPA
"""

import cv2
import numpy as np
from ultralytics import YOLO
import sys
import os
import platform
import argparse
import time
from datetime import datetime
from time import gmtime, localtime, strftime, sleep
import json
from astral import LocationInfo
from astral.sun import sun
import zoneinfo

start_time = time.time()

LOGDIR = "/cam/"
LOGFILE = "MPA_Detect.log"

# --- PARAMETERS INSTELLEN ---
parser = argparse.ArgumentParser(description='Auto MPA Detector')
parser.add_argument('input', help='Pad naar het mp4 bestand')
parser.add_argument('--verbose', action='store_true', help='Toon video window')
parser.add_argument('--output', action='store_true', help='Sla resultaat op als mp4')
parser.add_argument('--allclasses', action='store_true', help='Toon ook fiets, persoon, ...')
parser.add_argument('--dark', action='store_true', help='Forceer donker')
parser.add_argument('--light', action='store_true', help='Forceer licht')
parser.add_argument('--twilight', action='store_true', help='Forceer schemer')
args = parser.parse_args()

video_path = args.input

system = platform.system()
if system == "Windows":
  model = YOLO("yolo11n.onnx", task="detect")
else:
  model = YOLO("yolo11n_ncnn_model")

cap = cv2.VideoCapture(video_path)

# --- VIDEO OPSLAAN (Alleen als --output aan staat) ---
out = None
if args.output:
  # --- VIDEO OPSLAAN INSTELLINGEN ---
  # Pak de eigenschappen van de originele video
  frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
  frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
  fps = int(cap.get(cv2.CAP_PROP_FPS))
  # Definieer de codec en maak het VideoWriter object
  # 'mp4v' werkt meestal het best voor .mp4 bestanden
  fourcc = cv2.VideoWriter_fourcc(*'mp4v')
  #output_path = os.path.splitext(video_path)[0] + "_detected.mp4"
  # Haal alle extensies weg (ook .processing en .mp4)
  base_name = video_path
  while os.path.splitext(base_name)[1] in ['.mp4', '.processing', '.done']:
    base_name = os.path.splitext(base_name)[0]

  output_path = base_name + "_detected.mp4"

  out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))




firstTime = True
max1 = 0
max2 = 0

########################################################################
#                                                                      #
#       main                                                           #
#                                                                      #
########################################################################
def main():
  global firstTime, out, cap
  global max1, max2

  detector = LightConditionDetector(51.22, 4.40)
  cond = detector.get_condition()

  # Override cond for debugging purposes if this is requested from args
  if args.dark: cond = "donker"
  if args.light: cond = "licht"
  if args.twilight: cond = "schemer"

  logger(f"MPA_Detect.py started, condition:{cond}")
  logger(f"file:{video_path}")

  # Gebruik polygoon uit het hulpprogramma.
  #area_points = np.array([[265, 142], [317, 140], [530, 241], [315, 262], [265, 142]], np.int32)
  #area_points = np.array([[234, 168], [300, 158], [446, 235], [375, 256], [258, 267], [235, 169]], np.int32)
  # --- ROI INLADEN ---
  CONFIG_FILE = "roi_config.json"
  first_frame = None

  try:
    with open(CONFIG_FILE, "r") as f:
      loaded_points = json.load(f)
    area_points = np.array(loaded_points, np.int32)
    logger(f"ROI succesvol ingeladen vanuit {CONFIG_FILE}")
  except Exception as e:
    # Fallback voor als het bestand niet bestaat of corrupt is
    logger(f"FOUT: Kon {CONFIG_FILE} niet laden. Gebruik standaard waarden. Error: {e}")
    area_points = np.array([[234, 168], [300, 158], [446, 235], [375, 256], [258, 267], [235, 169]], np.int32)

  alreadyDetected = False
  while True:
    ret, frame = cap.read()
    if not ret:
      if firstTime:
        logger("Kan mp4 niet openen.")
      else:
        logger(f"Einde clip {max1} {max2}.")
      break
    if firstTime: first_frame = frame.copy()
    firstTime = False
    results = model(frame, stream=True, verbose=False)

    for r in results:
      for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = int((x1 + x2) / 2), int(y2)

        inside = cv2.pointPolygonTest(area_points, (cx, cy), False)
        categorie = model.names[int(box.cls[0])]

        if categorie != 'car' and args.allclasses:
          conf = box.conf[0]
          if conf > 0.4:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (175, 175, 175), 2)
            cv2.putText(frame, f"{categorie} {conf:.2f}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (175, 175, 175), 2)
            logger(f"no car:{categorie} c:{conf:.2f}")

        if inside >= 0 and categorie == 'car':
          hit_counter = 0

          auto_roi = frame[y1:y2, x1:x2]
          if auto_roi.size == 0: continue
          #bgr_color = get_dominant_color(auto_roi)
          #color_name = get_color_name(bgr_color)

          # 1. Bepaal de zone direct boven de auto (bijv. 20 pixels hoog)
          car_height = y2 - y1
          roof_height = int(car_height * 0.13)
          roof_gapheight = int(roof_height * 0.2)
          roof_y1 = y1 - roof_height - roof_gapheight
          roof_y2 = y1 - roof_gapheight

          car_width = x2 - x1
          margin_left = int(car_width * 0.2)
          margin_right = int(car_width * 0.33)
          roof_x1 = x1 + margin_left
          roof_x2 = x2 - margin_right

          car_aspect = car_width / car_height
          car_conf = float(box.conf[0])

          if car_conf < 0.5 or car_height < 80: continue   # skip dure berekeningen

          cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
          #cv2.putText(frame, f"car {color_name}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
          cv2.putText(frame, f"car {car_width}x{car_height} c:{car_conf:.2f}", (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

          # EXTRA DEBUGINFO ####
          # --- Bepaal positie voor extra debug info, linksonder in het frame.
          # We nemen 30 pixels marge van de onderkant en de zijkant
          text_x = 20
          text_y = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 30

          # De tekst die we gaan tonen
          coord_text = f"X:{x1} Y:{y1} aspect:{car_aspect:.2f}"

          # Teken de tekst op het frame (in het groen: (0, 255, 0))
          cv2.putText(frame, coord_text, (text_x, text_y),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
          ######################


          # Snij de nieuwe, kleinere ROI uit.
          roof_roi = frame[roof_y1:roof_y2, roof_x1:roof_x2]
          if roof_roi is None or roof_roi.size == 0: continue

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

          increased = False
          if white_percentage > max1:
            max1 = white_percentage
            increased = True
          if white_pixel_count > max2:
            max2 = white_pixel_count
            increased = True
          #if increased: logger(f"aant:{max2} perc:{max1}")
          # Omzetten naar grijswaarden om lichtheid te meten
          gray_roof = cv2.cvtColor(roof_roi, cv2.COLOR_BGR2GRAY)

          # Bereken het gemiddelde van de helderste pixels
          # We kijken of er een significant 'licht' blok bovenop staat
          avg_brightness = np.mean(gray_roof)

          # kleur van dakkoffer proberen te bepalen
          #bgr_color = get_dominant_color(roof_roi)
          #color_name = get_color_name(bgr_color)

          # Als de helderheid boven een drempel komt (bijv. 180 voor wit/lichtgrijs)
          if avg_brightness > 100:
            mean, std_dev = cv2.meanStdDev(roof_roi)

            # A smaller std_dev means higher homogeneity.
            homogeneity = int(std_dev[0][0])
            #print(f"Homogeneity score (lower is better): {homogeneity}")

            cv2.putText(frame, f"MPA w:{white_percentage} h:{homogeneity} s:{avg_saturation} {percentage_diff:.1f}", (x1, roof_y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.rectangle(frame, (roof_x1, roof_y1), (roof_x2, roof_y2), (255, 0, 0), 2)

            """
            decision = (
              white_percentage > 7 and
              homogeneity < 65 and
              avg_saturation < 15 and
              car_height > 90 and
              car_conf > 0.4
            )
            if cond == "licht":
              decision = (
                white_percentage > 15 and
                homogeneity < 50 and
                avg_saturation < 15 and
                car_height > 90 and
                car_conf > 0.5
              )
            """
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
              f"aspect:{car_aspect:.2f} conf:{car_conf:.2f} diff:{percentage_diff:.1f}"
            )

            #if hit_counter >= 3 and not alreadyDetected:
            if decision:
              text_x = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) - 100
              text_y = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) - 30

              cv2.putText(frame, "MPA!", (text_x, text_y),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

              if not alreadyDetected:
                alreadyDetected = True

                # Genereer de bestandsnaam voor de foto.
                # We pakken de naam van de video en veranderen de extensie naar .jpg
                image_filename = os.path.splitext(video_path)[0] + ".jpg"
                logger(f"MPA car detected! Snapshot stored as: {image_filename}")
                # Sla het huidige frame op.
                cv2.imwrite(image_filename, frame)

                if not args.verbose:
                  if out: out.write(frame) # veroorzakend frame ook in video zetten.
                  cap.release()
                  if out: out.release()
                  cv2.destroyAllWindows()
                  duurtijd = time.time() - start_time
                  logger(f"--- {duurtijd:.3f} seconds ---")

                  sys.exit(10)


    # Teken de polygoon op het beeld zodat je die ook in de video ziet.
    cv2.polylines(frame, [area_points], True, (0, 0, 255), 2)

    # --- OPSLAAN EN TONEN (Conditioneel) ---
    if out: out.write(frame)

    if args.verbose:
      cv2.imshow("Debug View", frame)
      if cv2.waitKey(1) & 0xFF == ord('q'):
        break

  # Netjes afsluiten.
  cap.release()
  if out: out.release()
  cv2.destroyAllWindows()
  duurtijd = time.time() - start_time
  logger(f"--- {duurtijd:.3f} seconds ---")

########################################################################
#                                                                      #
#       get_dominant_color                                             #
#                                                                      #
########################################################################
def get_dominant_color(roi):
  # Verklein de ROI om ruiten en wielen minder gewicht te geven
  # We pakken alleen het midden van de auto
  h, w, _ = roi.shape
  roi_center = roi[int(h*0.3):int(h*0.8), int(w*0.2):int(w*0.8)]

  # Maak een lijst van de kleuren en zoek de meest voorkomende
  data = np.reshape(roi_center, (-1, 3))
  data = np.float32(data)

  # We clusteren de kleuren in 3 groepen (K-means) om uitschieters te middelen
  criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
  flags = cv2.KMEANS_RANDOM_CENTERS
  compactness, labels, centers = cv2.kmeans(data, 3, None, criteria, 10, flags)

  # De meest voorkomende cluster is de hoofdkleur
  dominant_bgr = centers[np.argmax(np.bincount(labels.flatten()))]
  return dominant_bgr.astype(int)

########################################################################
#                                                                      #
#       get_color_name                                                 #
#                                                                      #
########################################################################
def get_color_name(bgr_color):
  # Omzetten naar HSV (OpenCV verwacht een 1x1 pixel array)
  hsv_color = cv2.cvtColor(np.uint8([[bgr_color]]), cv2.COLOR_BGR2HSV)[0][0]
  h, s, v = hsv_color

  # 1. Check eerst op grijswaarden (lage verzadiging)
  if s < 40:
    if v < 50: return "Zwart"
    if v > 200: return "Wit"
    return "Grijs"

  # 2. Bepaal de kleur op basis van de Hue (H)
  if h < 10 or h > 160: return "Rood"
  if h < 25: return "Oranje"
  if h < 35: return "Geel"
  if h < 85: return "Groen"
  if h < 130: return "Blauw"
  if h < 145: return "Violet"
  if h < 160: return "Roze"

  return "Onbekend"

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
