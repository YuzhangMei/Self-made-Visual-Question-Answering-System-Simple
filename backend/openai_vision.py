import base64
import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

SYSTEM_PROMPT = """You are an accessibility assistant.
Your job: Given an image, output a structured object list for blind/low-vision users.

Return ONLY valid JSON (no markdown, no extra text).
The JSON must follow this structure:
{
  "objects": [
    {
      "id": <int starting from 1>,
      "name": <string>,
      "count": <int>,
      "color": <string or null>,
      "position": <string: left/middle/right + optional top/middle/bottom>,
      "attributes": <array of short strings, can be empty>
    }
  ]
}

Guidelines:
- Include all salient objects.
- Use approximate positions like: "left", "right", "middle", "top-left", "bottom-right".
- If count is unknown, guess a reasonable integer.
- If color not visible, use null.
"""

def _to_data_url(image_bytes: bytes, mime: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def analyze_image_to_objects(
    image_bytes: bytes,
    mime_type: str,
    question: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 600,
) -> Dict[str, Any]:
    """
    Calls OpenAI vision model and returns a parsed JSON dict:
    { "objects": [...] }
    """
    data_url = _to_data_url(image_bytes, mime_type)

    user_text = f"""User question: {question}

Task:
1) Identify objects relevant for answering the question, but still include other salient objects.
2) Produce the JSON object list as specified.
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            },
        ],
        # JSON mode: ensures the output is valid JSON (not necessarily schema-perfect)
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=0.2,
    )

    content = resp.choices[0].message.content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model returned non-JSON content: {content[:200]}...") from e

    # Minimal validation + normalization
    if "objects" not in parsed or not isinstance(parsed["objects"], list):
        raise ValueError(f"JSON missing 'objects' list. Got: {parsed}")

    # Ensure ids are ints starting at 1 (best-effort fix)
    for i, obj in enumerate(parsed["objects"], start=1):
        if not isinstance(obj, dict):
            continue
        obj["id"] = int(obj.get("id", i)) if str(obj.get("id", "")).isdigit() else i
        if "count" in obj:
            try:
                obj["count"] = int(obj["count"])
            except Exception:
                obj["count"] = 1
        else:
            obj["count"] = 1
        if "attributes" not in obj or not isinstance(obj["attributes"], list):
            obj["attributes"] = []

    return parsed
