import cv2
import time
import subprocess

TIMEOUT = 3  # seconds without motion before muting
ROOM_A = "livingroom"
ROOM_B = "bedroom"  # match your env var name: $roku_ip_livingromm

LEAVE_CMD = [
    "zsh", "-lc",
    f"source ~/sync/.funcrc && roku_handoff_mute {ROOM_A} {ROOM_B}"
]

RETURN_CMD = [
    "zsh", "-lc",
    f"source ~/sync/.funcrc && roku_handoff_mute {ROOM_B} {ROOM_A}"
]

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("Could not open webcam")

ret, prev = cap.read()
prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

last_motion = time.time()
present = True  # assume you start in the room

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    diff = cv2.absdiff(prev_gray, gray)
    thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
    motion_pixels = thresh.sum()

    now = time.time()

    # Motion detected
    if motion_pixels > 5000:
        last_motion = now
        if not present:
            subprocess.run(RETURN_CMD)
            present = True

    # No motion for TIMEOUT seconds
    elif present and now - last_motion > TIMEOUT:
        subprocess.run(LEAVE_CMD)
        present = False

    prev_gray = gray
    time.sleep(0.2)

