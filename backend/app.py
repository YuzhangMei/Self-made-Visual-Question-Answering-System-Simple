from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
from video_processor import extract_frames
from temporal_aggregator import aggregate_temporal_objects
import os
import uuid
import hashlib

from openai_vision import analyze_image_to_objects
from ambiguity import detect_ambiguity
from response_generator import generate_onepass_response
from llm_answer import generate_natural_answer
from session_store import (
    create_session,
    get_session,
    end_session,
    set_focus_object,
    append_history,
)

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov"}
EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def compute_image_signature(image_bytes: bytes) -> str:
    return hashlib.sha1(image_bytes).hexdigest()


def analyze_video(video_path, question, mode):

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    frames = extract_frames(video_bytes)

    frame_results = []

    for frame_bytes, timestamp in frames:
        parsed = analyze_image_to_objects(
            image_bytes=frame_bytes,
            mime_type="image/jpeg",
            question=question,
        )
        objects = parsed.get("objects", [])
        frame_results.append((timestamp, objects))

    temporal_objects = aggregate_temporal_objects(frame_results)

    # simple ambiguity
    ambiguity = {
        "is_ambiguous": len(temporal_objects) > 1,
        "reasons": ["Objects appear across multiple time points"],
    }

    answer_lines = []

    for obj in temporal_objects:
        answer_lines.append(
            f"{obj['name']} appears from {obj['first_seen']} to {obj['last_seen']}."
        )

    answer = "\n".join(answer_lines)

    return jsonify({
        "ok": True,
        "mode": "video",
        "answer": answer,
        "temporal_objects": temporal_objects,
        "ambiguity": ambiguity
    })


@app.route("/")
def home():
    return "Backend running"


# ==========================
# ANALYZE (First round)
# ==========================
@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "Missing image"}), 400

    image = request.files["image"]
    question = request.form.get("question", "").strip()
    mode = request.form.get("mode", "onepass").strip()

    if not question:
        return jsonify({"error": "Missing question"}), 400

    original_name = secure_filename(image.filename)
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Unsupported file type"}), 400

    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    image.save(saved_path)
    if ext in [".mp4", ".mov"]:
        return analyze_video(saved_path, question, mode)

    with open(saved_path, "rb") as f:
        image_bytes = f.read()

    image_sig = compute_image_signature(image_bytes)
    mime_type = EXT_TO_MIME.get(ext, "image/jpeg")

    parsed = analyze_image_to_objects(
        image_bytes=image_bytes,
        mime_type=mime_type,
        question=question,
    )

    objects = parsed.get("objects", [])
    ambiguity = detect_ambiguity(question, objects)

    # ---------------- One-pass ----------------
    if mode == "onepass":
        answer = generate_onepass_response(objects, ambiguity=ambiguity)

        return jsonify({
            "ok": True,
            "mode": mode,
            "answer": answer,
            "ambiguity": ambiguity
        })

    # ---------------- Clarify ----------------
    elif mode == "clarify":

        if ambiguity["is_ambiguous"]:

            session_id = create_session({
                "objects": objects,
                "question": question,
                "image_signature": image_sig,
            })

            append_history(session_id, "user", question)
            append_history(session_id, "assistant", ambiguity["clarifying_question"])

            return jsonify({
                "ok": True,
                "mode": mode,
                "session_id": session_id,
                "clarification": {
                    "question": ambiguity["clarifying_question"],
                    "options": ambiguity["options"],
                }
            })

        else:
            # no ambiguity, answer directly
            selected_object = objects[0] if objects else None

            answer = generate_natural_answer(
                question=question,
                selected_object=selected_object,
                all_objects=objects
            )

            return jsonify({
                "ok": True,
                "answer": answer
            })

    return jsonify({"error": "Invalid mode"}), 400


# ==========================
# CLARIFY (Second round)
# ==========================
@app.route("/clarify", methods=["POST"])
def clarify():
    data = request.json
    session_id = data.get("session_id")
    selection = data.get("selection")

    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session expired or invalid"}), 400

    objects = session.get("objects", [])
    question = session.get("question")

    selected_object = None
    for obj in objects:
        label = f"{obj.get('name')} #{obj.get('id')}"
        if label in selection:
            selected_object = obj
            break

    if not selected_object:
        for obj in objects:
            if obj.get("name", "").lower() in selection.lower():
                selected_object = obj
                break

    if not selected_object:
        return jsonify({"error": "Could not match selection"}), 400

    set_focus_object(session_id, selected_object)

    answer = generate_natural_answer(
        question=question,
        selected_object=selected_object,
        all_objects=objects
    )

    append_history(session_id, "assistant", answer)

    return jsonify({
        "ok": True,
        "answer": answer,
        "focus_ready": True
    })


# ==========================
# FOLLOW-UP CHAT (Third+ rounds)
# ==========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id")
    user_text = data.get("text", "").strip()

    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session expired"}), 400

    focus = session.get("focus_object")
    if not focus:
        return jsonify({"error": "No focus object selected"}), 400

    objects = session.get("objects", [])

    append_history(session_id, "user", user_text)

    answer = generate_natural_answer(
        question=user_text,
        selected_object=focus,
        all_objects=objects
    )

    append_history(session_id, "assistant", answer)

    return jsonify({
        "ok": True,
        "answer": answer
    })


# ==========================
# END SESSION
# ==========================
@app.route("/end_session", methods=["POST"])
def end_session_route():
    data = request.json
    session_id = data.get("session_id")

    end_session(session_id)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
