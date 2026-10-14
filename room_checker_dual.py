import argparse
import cv2
from pathlib import Path
import subprocess
import time

MOTION_THRESHOLD_DEFAULT = 5000
ROOMS = ("livingroom", "bedroom")
STATE_UNKNOWN = "unknown"


def build_cmd(source_room: str, target_room: str):
    return [
        "zsh",
        "-lc",
        f"source ~/sync/.funcrc && roku_handoff_mute {source_room} {target_room}",
    ]


def read_muted_room(state_file: Path) -> str:
    try:
        value = state_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return STATE_UNKNOWN

    if value in ROOMS:
        return value
    return STATE_UNKNOWN


def write_muted_room(state_file: Path, muted_room: str) -> None:
    state_file.write_text(f"{muted_room}\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Use shared state to handoff audio between rooms when motion is seen. "
            "Use --present-in to define which room this laptop is in."
        )
    )
    parser.add_argument(
        "--present-in",
        required=True,
        choices=list(ROOMS),
        help="Room this laptop is located in",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=MOTION_THRESHOLD_DEFAULT,
        help="Motion pixel sum threshold",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="OpenCV camera index",
    )
    parser.add_argument(
        "--state-file",
        default="room_muted_state.txt",
        help="Synced file containing currently muted room name",
    )
    parser.add_argument(
        "--init-muted",
        choices=list(ROOMS),
        help="Initialize state file on startup if it does not exist",
    )
    args = parser.parse_args()

    state_file = Path(args.state_file)
    if args.init_muted and not state_file.exists():
        write_muted_room(state_file, args.init_muted)

    other_room = next(room for room in ROOMS if room != args.present_in)
    handoff_cmd = build_cmd(other_room, args.present_in)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    ret, prev = cap.read()
    if not ret:
        raise RuntimeError("Could not read initial frame")

    prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)

    motion_active = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        diff = cv2.absdiff(prev_gray, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        motion_pixels = int(thresh.sum())

        has_motion = motion_pixels > args.threshold

        # Trigger once per motion burst.
        if has_motion and not motion_active:
            muted_room = read_muted_room(state_file)
            if muted_room == args.present_in or muted_room == STATE_UNKNOWN:
                result = subprocess.run(handoff_cmd)
                if result.returncode == 0:
                    write_muted_room(state_file, other_room)

        motion_active = has_motion
        prev_gray = gray
        time.sleep(0.2)


if __name__ == "__main__":
    main()
