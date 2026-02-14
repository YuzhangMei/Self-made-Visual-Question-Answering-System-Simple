import cv2
import tempfile
import os


def extract_frames(video_bytes, max_frames=5):
    """
    Extract evenly spaced frames from short video.
    Returns list of (frame_bytes, timestamp_str)
    """

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if total_frames == 0 or fps == 0:
        cap.release()
        os.remove(tmp_path)
        return []

    duration = total_frames / fps

    frame_indices = []
    for i in range(max_frames):
        t = duration * i / max_frames
        frame_index = int(t * fps)
        frame_indices.append(frame_index)

    frames = []

    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        timestamp = f"{round(idx / fps, 2)}s"
        frames.append((frame_bytes, timestamp))

    cap.release()
    os.remove(tmp_path)

    return frames
