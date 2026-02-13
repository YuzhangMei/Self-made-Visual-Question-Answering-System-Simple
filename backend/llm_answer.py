import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

SYSTEM_PROMPT = """You are an accessibility assistant helping blind or low-vision users.

Your job:
Given:
- the user's question
- the selected object information
- the full scene object list

Generate a clear, natural, concise description that directly answers the user's question.

Guidelines:
- Be clear and structured.
- Mention object name, color, and position if available.
- Avoid unnecessary verbosity.
- Use accessible phrasing suitable for screen readers.
"""

def generate_natural_answer(question, selected_object, all_objects):
    prompt = f"""
User question:
{question}

Selected object:
{selected_object}

All detected objects:
{all_objects}

Generate the final answer.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()
