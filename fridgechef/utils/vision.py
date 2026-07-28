import base64
import io
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

VISION_MODEL = "google/gemma-4-26b-a4b-it:free"

SYSTEM_PROMPT = (
    "당신은 냉장고 사진에서 식재료를 인식하는 비전 어시스턴트입니다. "
    "이미지에 보이는 식재료의 이름만 한국어로, 다른 설명 없이 JSON 배열 형태로만 답하세요. "
    '예시: ["계란", "대파", "두부", "김치"]'
)


def _resize_image(image_bytes: bytes, max_side: int = 1024) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def recognize_ingredients(image_bytes: bytes) -> list[str]:
    resized = _resize_image(image_bytes)
    b64 = base64.b64encode(resized).decode("utf-8")

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "이 냉장고 사진에서 식재료를 인식해줘."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()

    array_match = re.search(r"\[.*\]", raw, flags=re.DOTALL)
    json_candidate = array_match.group(0) if array_match else raw

    try:
        ingredients = json.loads(json_candidate)
        if isinstance(ingredients, list):
            return [str(i).strip() for i in ingredients if str(i).strip()]
    except json.JSONDecodeError:
        pass
    fallback = [s.strip(" -•`\"'[]") for s in raw.replace(",", "\n").splitlines()]
    return [s for s in fallback if s]
