import os
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
from openai_vision import analyze_image_to_objects
from ambiguity import detect_ambiguity
from response_generator import generate_final_answer, generate_onepass_response
from session_store import create_session, get_session
from llm_answer import generate_natural_answer

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}  # docs supported types include these :contentReference[oaicite:6]{index=6}
EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

@app.route("/")
def home():
    return "Backend running"

@app.route("/test")
def test():
    return jsonify({"message": "Hello from Flask backend!"})

@app.route("/analyze", methods=["POST"])
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "Missing 'image' file field"}), 400

    image = request.files["image"]
    if image.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    question = request.form.get("question", "").strip()
    mode = request.form.get("mode", "onepass").strip()

    if not question:
        return jsonify({"error": "Missing 'question' text field"}), 400

    original_name = secure_filename(image.filename)
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400

    # Save image (debug)
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    image.save(saved_path)

    # Read bytes for model call
    with open(saved_path, "rb") as f:
        image_bytes = f.read()

    mime_type = EXT_TO_MIME.get(ext, "image/jpeg")

    try:
        parsed = analyze_image_to_objects(
            image_bytes=image_bytes,
            mime_type=mime_type,
            question=question,
        )
        objects = parsed.get("objects", [])
    except Exception as e:
        return jsonify({"error": f"Vision model call failed: {str(e)}"}), 500

    # Ambiguity detection
    ambiguity = detect_ambiguity(question, objects)

    # Step 5: Mode-based routing
    if mode == "onepass":
        answer_text = generate_onepass_response(objects)
        response = {
            "ok": True,
            "mode": mode,
            "question": question,
            "objects": objects,
            "ambiguity": ambiguity,
            "answer": answer_text,
        }

    elif mode == "clarify":
        if ambiguity["is_ambiguous"]:
            # Step 6: 创建 session 存储当前 objects
            session_id = create_session({
                "objects": objects,
                "question": question
            })
            response = {
                "ok": True,
                "mode": mode,
                "session_id": session_id,
                "clarification": {
                    "question": ambiguity["clarifying_question"],
                    "options": ambiguity["options"],
                }
            }
        else:
            if not objects:
                return jsonify({
                    "ok": True,
                    "mode": mode,
                    "answer": "I do not see any relevant objects."
                })

            selected_object = objects[0]

            try:
                answer = generate_natural_answer(
                    question=question,
                    selected_object=selected_object,
                    all_objects=objects
                )
            except Exception as e:
                return jsonify({"error": f"LLM answer generation failed: {str(e)}"}), 500

            return jsonify({
                "ok": True,
                "mode": mode,
                "answer": answer
            })

    else:
        return jsonify({"error": "Invalid mode"}), 400

    return jsonify(response)


@app.route("/clarify", methods=["POST"])
def clarify():
    data = request.json

    session_id = data.get("session_id")
    selection = data.get("selection")

    if not session_id or not selection:
        return jsonify({"error": "Missing session_id or selection"}), 400

    session = get_session(session_id)

    if not session:
        return jsonify({"error": "Invalid session"}), 400

    objects = session.get("objects", [])
    question = session.get("question")

    # 简单匹配逻辑（根据 selection 文本匹配 id）
    selected_object = None
    for obj in objects:
        label = f"{obj.get('name')} #{obj.get('id')}"
        if label in selection:
            selected_object = obj
            break

    if not selected_object:
        # fallback：匹配名称
        for obj in objects:
            if obj.get("name") in selection.lower():
                selected_object = obj
                break

    if not selected_object:
        return jsonify({"error": "Could not match selection"}), 400

    # ---- Generate natural answer via LLM ----
    try:
        answer = generate_natural_answer(
            question=question,
            selected_object=selected_object,
            all_objects=objects
        )
    except Exception as e:
        return jsonify({"error": f"LLM answer generation failed: {str(e)}"}), 500

    return jsonify({
        "ok": True,
        "answer": answer
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
