import argparse
import time
import threading
import requests
import numpy as np
import cv2
import sys

def fetch_loop(url, session, frame_holder, stop_event, fps):
    interval = 1.0 / fps if fps > 0 else 0.1
    while not stop_event.is_set():
        try:
            r = session.get(url, timeout=5)
            if r.status_code == 200:
                arr = np.frombuffer(r.content, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    frame_holder[0] = img
                else:
                    # decode fail
                    pass
            else:
                pass
        except Exception as e:
            pass
        time.sleep(interval)

def rtsp_loop(rtsp_url, frame_holder, stop_event):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("[!] Failed to open RTSP stream:", rtsp_url)
        return
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            # small sleep then retry
            time.sleep(0.1)
            continue
        frame_holder[0] = frame
    cap.release()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Snapshot URL (full URL to JPEG snapshot)", type=str)
    parser.add_argument("--rtsp", help="RTSP URL (optional, if supported)", type=str)
    parser.add_argument("--fps", help="Target FPS for snapshot fetching (default 10)", type=float, default=10.0)
    parser.add_argument("--scale", help="Scale factor for display (0.5, 1.0 etc)", type=float, default=1.0)
    parser.add_argument("--show-fps", help="Overlay current FPS on window", action="store_true")
    args = parser.parse_args()

    if not args.url and not args.rtsp:
        print("You must provide --url (snapshot) or --rtsp. See --help.")
        sys.exit(1)

    stop_event = threading.Event()
    frame_holder = [None]  
    if args.rtsp:
        t = threading.Thread(target=rtsp_loop, args=(args.rtsp, frame_holder, stop_event), daemon=True)
        t.start()
    else:
        session = requests.Session()
        session.headers.update({"User-Agent": "snapshot-stream/1.0"})
        t = threading.Thread(target=fetch_loop, args=(args.url, session, frame_holder, stop_event, args.fps), daemon=True)
        t.start()

    win_name = "Camera Stream (press q to quit)"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)

    prev_time = time.time()
    frames_shown = 0
    fps_calc = 0.0

    try:
        while True:
            frame = frame_holder[0]
            if frame is not None:
                # optionally scale for display
                if args.scale != 1.0:
                    h, w = frame.shape[:2]
                    frame = cv2.resize(frame, (int(w * args.scale), int(h * args.scale)))

                if args.show_fps:
                    frames_shown += 1
                    now = time.time()
                    elapsed = now - prev_time
                    if elapsed >= 1.0:
                        fps_calc = frames_shown / elapsed
                        frames_shown = 0
                        prev_time = now
                    cv2.putText(frame, f"{fps_calc:.1f} FPS", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

                cv2.imshow(win_name, frame)
            else:
                # no frame yet - show black screen with message
                black = np.zeros((240, 320, 3), dtype=np.uint8)
                cv2.putText(black, "Waiting for frame...", (10,120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 2)
                cv2.imshow(win_name, black)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            time.sleep(0.001)

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        cv2.destroyAllWindows()
        print("Exiting...")

if __name__ == "__main__":
    main()
