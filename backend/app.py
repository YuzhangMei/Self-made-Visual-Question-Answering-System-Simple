import os
import uuid
import hashlib

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from video_processor import extract_frames
from temporal_aggregator import aggregate_temporal_objects
from temporal_ambiguity import detect_temporal_ambiguity
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
    ".mp4": "video/mp4",
    ".mov": "video/mov",
}


def compute_image_signature(image_bytes: bytes) -> str:
    "Make SHA1 has for the image"
    return hashlib.sha1(image_bytes).hexdigest()


def analyze_video(video_path, question, mode):
    """
    Handle video input:
    - Extract frames
    - Analyze each frame with vision model
    - Aggregate temporal objects
    - Support onepass and clarify modes
    """
    # Load video bytes
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    # Extract frames for convertion to image identification
    frames = extract_frames(video_bytes)
    if not frames:
        return jsonify({
            "error": "Could not extract frames from video."
        }), 400

    # Analyze each frame
    frame_results = []
    for frame_bytes, timestamp in frames:
        parsed = analyze_image_to_objects(
            image_bytes=frame_bytes,
            mime_type="image/jpeg",
            question=question,
        )
        objects = parsed.get("objects", [])
        frame_results.append((timestamp, objects))

    # Temporal aggregation
    temporal_objects = aggregate_temporal_objects(frame_results)
    if not temporal_objects:
        return jsonify({
            "ok": True,
            "mode": "video",
            "answer": "No salient objects detected in the video."
        })

    # Detect temporal ambiguity
    ambiguity = detect_temporal_ambiguity(question, temporal_objects)

    # MODE-specific process
    # CLARIFY MODE: Clarify Iteratively
    if mode == "clarify":
        # Ambiguous -> Create session and return options
        # for multi-turn interaction
        if ambiguity.get("is_ambiguous"):
            session_id = create_session({
                "objects": temporal_objects,
                "question": question,
                "type": "video",
            })
            append_history(session_id, "user", question)
            append_history(session_id, "assistant", ambiguity["clarifying_question"])
            return jsonify({
                "ok": True,
                "mode": "clarify",
                "session_id": session_id,
                "clarification": {
                    "question": ambiguity["clarifying_question"],
                    "options": ambiguity["options"],
                }
            })
        else:
            # Unambiguous → answer directly
            selected_object = temporal_objects[0]
            answer = generate_natural_answer(
                question=question,
                selected_object=selected_object,
                all_objects=temporal_objects,
                temporal=True
            )
            return jsonify({
                "ok": True,
                "mode": "video",
                "answer": answer
            })

    # ONEPASS MODE: Respond in one pass
    answer_lines = []
    for obj in temporal_objects:
        first = obj["first_seen"]
        last = obj["last_seen"]
        name = obj["name"]
        if first == last:
            line = f"{name} appears at {first}."
        else:
            line = f"{name} appears from {first} to {last}."
        answer_lines.append(line)
    answer_lines.append("")
    answer_lines.append(
        "Note: appearance times are based on sampled key frames."
    )
    return jsonify({
        "ok": True,
        "mode": "video",
        "answer": "\n".join(answer_lines),
        "temporal_objects": temporal_objects,
        "ambiguity": ambiguity
    })


@app.route("/")
def home():
    "Verify the status of Backend."
    return "Backend running"


@app.route("/analyze", methods=["POST"])
def analyze():
    "Analyze the first-round image or video."
    if "image" not in request.files:
        return jsonify({"error": "Missing image"}), 400
    
    image = request.files["image"]
    mode = request.form.get("mode", "onepass").strip()
    question = request.form.get("question", "").strip()
    if not question:
        return jsonify({"error": "Missing question"}), 400

    original_name = secure_filename(image.filename)
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "Unsupported file type"}), 400

    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    image.save(saved_path)
    # Activate video analysis function if the input is video stream
    if ext in [".mp4", ".mov"]:
        return analyze_video(saved_path, question, mode)
    # Or otherwise analyze image and feed the image to vision model
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

    # MODE-specific process
    # ONEPASS MODE: Respond in one pass
    if mode == "onepass":
        answer = generate_onepass_response(objects, ambiguity=ambiguity)
        return jsonify({
            "ok": True,
            "mode": mode,
            "answer": answer,
            "ambiguity": ambiguity
        })
    # CLARIFY MODE: Clarify Iteratively
    elif mode == "clarify":
        # Ambiguous -> Create session and return options
        # for multi-turn interaction
        if ambiguity["is_ambiguous"]:
            session_id = create_session({
                "objects": objects,
                "question": question,
                "image_signature": image_sig,
                "type": "image"
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
        # Unambiguous → answer directly
        else:
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


@app.route("/clarify", methods=["POST"])
def clarify():
    """
    Second-round interaction for clarification options
    (specifically for clarify mode)
    """
    data = request.json or {}
    session_id = data.get("session_id")
    selection = (data.get("selection") or "").strip()
    if not session_id or not selection:
        return jsonify({"error": "Missing session_id or selection"}), 400
    
    session = get_session(session_id)
    if not session:
        return jsonify({"error": "Session expired or invalid"}), 400
    
    question = session.get("question", "")
    session_type = session.get("type", "image")
    objects = session.get("objects", [])
    if not objects:
        return jsonify({"error": "Session has no objects"}), 400
    selected_object = None

    # Image session matching -> name #id + fallback by name
    if session_type == "image":
        # Try match by "name #id"
        for obj in objects:
            obj_name = str(obj.get("name", "")).strip()
            obj_id = obj.get("id", None)
            label = f"{obj_name} #{obj_id}"
            if obj_name and obj_id is not None and label in selection:
                selected_object = obj
                break
        # Fallback by name
        if not selected_object:
            sel_lower = selection.lower()
            for obj in objects:
                obj_name = str(obj.get("name", "")).lower()
                if obj_name and obj_name in sel_lower:
                    selected_object = obj
                    break
        # Final fallback: if only one object, pick it
        if not selected_object and len(objects) == 1:
            selected_object = objects[0]

    # Video session matching -> temporal option strings + fallback by name
    # Objects are temporal_objects: 
    # {name, first_seen, last_seen, ...}
    else:
        sel_lower = selection.lower()
        # Prefer exact match with the option format
        # Options like: "vase (0.0s–4.77s)" or "vase at 1.17s"
        for obj in objects:
            name = str(obj.get("name", "")).strip()
            first = str(obj.get("first_seen", "")).strip()
            last = str(obj.get("last_seen", "")).strip()
            if not name:
                continue
            if first and last and first != last:
                option_label = f"{name} ({first}–{last})".lower()
            elif first:
                option_label = f"{name} at {first}".lower()
            else:
                option_label = name.lower()
            if option_label == sel_lower:
                selected_object = obj
                break
        # Fallback: match by name substring
        if not selected_object:
            for obj in objects:
                name = str(obj.get("name", "")).lower()
                if name and name in sel_lower:
                    selected_object = obj
                    break
        # Final fallback: if only one object, pick it
        if not selected_object and len(objects) == 1:
            selected_object = objects[0]

    if not selected_object:
        return jsonify({"error": "Could not match selection"}), 400
    
    # Set focus + record history
    set_focus_object(session_id, selected_object)
    append_history(session_id, "user", f"[selection] {selection}")

    # Generate answer (temporal sessions include time context)
    try:
        if session_type == "video":
            # Make time context explicit so LLM uses it
            first = selected_object.get("first_seen", "")
            last = selected_object.get("last_seen", "")
            name = selected_object.get("name", "object")

            temporal_context = f"The selected object is '{name}'. "
            if first and last and first != last:
                temporal_context += f"It appears from {first} to {last} in the video."
            elif first:
                temporal_context += f"It appears at {first} in the video."

            llm_question = (
                f"{question}\n\n"
                f"{temporal_context}\n"
                f"Answer the user's question with this time information in mind."
            )

            answer = generate_natural_answer(
                question=llm_question,
                selected_object=selected_object,
                all_objects=objects,
                temporal=True
            )
        else:
            answer = generate_natural_answer(
                question=question,
                selected_object=selected_object,
                all_objects=objects,
            )
    except Exception as e:
        return jsonify({"error": f"LLM answer generation failed: {str(e)}"}), 500
    append_history(session_id, "assistant", answer)
    return jsonify({
        "ok": True,
        "answer": answer,
        "focus_ready": True,
        "session_type": session_type
    })


@app.route("/chat", methods=["POST"])
def chat():
    "Follow-up chat for third+ rounds"
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

    session_type = session.get("type", "image")

    append_history(session_id, "user", user_text)

    answer = generate_natural_answer(
        question=user_text,
        selected_object=focus,
        all_objects=objects,
        temporal=(session_type == "video")
    )

    append_history(session_id, "assistant", answer)

    return jsonify({
        "ok": True,
        "answer": answer
    })


@app.route("/end_session", methods=["POST"])
def end_session_route():
    "End session"
    data = request.json
    session_id = data.get("session_id")
    end_session(session_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
