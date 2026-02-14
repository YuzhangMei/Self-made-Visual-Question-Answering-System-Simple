import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def generate_natural_answer(
    question: str,
    selected_object: dict,
    all_objects: list,
    temporal: bool = False
):
    """
    Generate natural language answer for:
    - Static image object
    - Temporal (video) object
    - Multi-turn follow-up
    """

    if not selected_object:
        return "I could not determine the selected object."

    # ==========================
    # STATIC OBJECT CONTEXT
    # ==========================
    if not temporal:

        name = selected_object.get("name", "object")
        color = selected_object.get("color", "unknown")
        position = selected_object.get("position", "unknown")
        attributes = selected_object.get("attributes", [])

        context = f"""
You are answering a question about an object detected in an image.

Selected Object:
- Name: {name}
- Color: {color}
- Position: {position}
- Attributes: {attributes}

All detected objects in the scene:
{all_objects}

Answer the user's question clearly and concisely.
If the question is a follow-up (e.g., "What color is it?"),
refer to the selected object.
"""

    # ==========================
    # TEMPORAL OBJECT CONTEXT
    # ==========================
    else:

        name = selected_object.get("name", "object")
        first_seen = selected_object.get("first_seen", "unknown")
        last_seen = selected_object.get("last_seen", "unknown")

        context = f"""
You are answering a question about an object detected in a video.

Selected Temporal Object:
- Name: {name}
- First seen at: {first_seen}
- Last seen at: {last_seen}

All temporal objects detected in the video:
{all_objects}

Answer the user's question clearly.
If the question refers to timing (e.g., when did it appear?),
use the first_seen and last_seen information.
"""

    # ==========================
    # Construct prompt
    # ==========================

    prompt = f"""
{context}

User Question:
{question}

Provide a helpful and natural response.
Do not invent objects not in the context.
"""

    # ==========================
    # Call OpenAI
    # ==========================

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating answer: {str(e)}"
