import cv2
import numpy as np
import argparse
import json

# --- PARAMETERS INSTELLEN ---
parser = argparse.ArgumentParser(description='Roi insteller')
parser.add_argument('input', help='Pad naar het mp4 of jpg bestand')
args = parser.parse_args()

points = []
img = None

########################################################################
#                                                                      #
#       main                                                           #
#                                                                      #
########################################################################
def main():
  global img

  # Vervang dit door je eigen screenshot of video-pad.
  # Je kunt ook een frame van de video pakken.
  cap = cv2.VideoCapture(args.input)
  ret, img = cap.read()
  cap.release()

  print("Instructies:")
  print("- Klik met LINKS om de hoekpunten van de weg te markeren (met de klok mee).")
  print("- Klik met RECHTS om opnieuw te beginnen.")
  print("- Druk op 'q' of 'ESC' als je klaar bent.")

  cv2.imshow("Selecteer Punten", img)
  cv2.setMouseCallback("Selecteer Punten", click_event)

  cv2.waitKey(0)
  cv2.destroyAllWindows()

  if points:
    #print("\nKopieer deze regel naar je hoofdscript:")
    #print(f"area_points = np.array({points}, np.int32)")
    # Sla de punten op naar een bestand
    config_file = "roi_config.json"
    with open(config_file, "w") as f:
      json.dump(points, f)

    print(f"\nPunten opgeslagen in {config_file}")
    print(f"Inhoud: {points}")

########################################################################
#                                                                      #
#       click_event                                                    #
#                                                                      #
########################################################################
def click_event(event, x, y, flags, params):
  # Linksklik om een punt toe te voegen.
  if event == cv2.EVENT_LBUTTONDOWN:
    points.append([x, y])
    # Teken een cirkeltje en verbind met het vorige punt.
    cv2.circle(img, (x, y), 5, (0, 0, 255), -1)
    if len(points) > 1:
      cv2.line(img, tuple(points[-2]), tuple(points[-1]), (0, 255, 0), 2)

    cv2.imshow("Selecteer Punten", img)
    print(f"Punt toegevoegd: [{x}, {y}]")

  # Rechtsklik om de lijst te wissen als je een fout maakt.
  elif event == cv2.EVENT_RBUTTONDOWN:
    points.clear()
    print("Punten gewist, begin opnieuw.")

########################################################################
#                                                                      #
#       Start main function.                                           #
#                                                                      #
########################################################################
main()
