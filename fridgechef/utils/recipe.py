import json
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

RECIPE_MODEL = "openai/gpt-oss-20b:free"

SYSTEM_PROMPT = (
    "당신은 냉장고 속 재료를 활용한 레시피를 추천하는 요리 어시스턴트입니다. "
    "반드시 JSON 형식으로만 답하고, 다른 설명 문장은 포함하지 마세요. "
    "recipes 배열에는 반드시 서로 다른 레시피를 2개 또는 3개 포함하세요 (1개만 반환하는 것은 허용되지 않습니다). "
    "title, used_ingredients, missing_ingredients, steps 등 모든 텍스트 값은 예외 없이 한국어로만 작성하세요. "
    "영어 단어나 재료명을 섞어 쓰지 마세요. "
    '형식: {"recipes": [{"title": str, "time_minutes": int, "servings": int, '
    '"used_ingredients": [str], "missing_ingredients": [str], "steps": [str]}]}'
)


def _extract_json(raw: str) -> str:
    raw = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    return match.group(0) if match else raw


def generate_recipes(
    ingredients: list[str],
    servings: int = 2,
    max_time_minutes: int | None = None,
    exclude: list[str] | None = None,
) -> list[dict]:
    conditions = [f"보유 재료: {', '.join(ingredients)}", f"인분 수: {servings}인분"]
    if max_time_minutes:
        conditions.append(f"조리 시간은 {max_time_minutes}분 이내")
    if exclude:
        conditions.append(f"다음 재료는 알레르기/비선호로 제외: {', '.join(exclude)}")

    user_prompt = "\n".join(conditions) + "\n\n위 조건에 맞는 레시피를 추천해줘."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(2):
        try:
            response = client.chat.completions.create(model=RECIPE_MODEL, messages=messages)
        except RateLimitError:
            if attempt == 0:
                time.sleep(2)
                continue
            raise

        raw = response.choices[0].message.content.strip()
        json_str = _extract_json(raw)
        try:
            data = json.loads(json_str)
            recipes = data.get("recipes", [])
            if recipes:
                return recipes
        except json.JSONDecodeError:
            pass
        # 응답이 비정상(파싱 실패/빈 목록)이면 1회 재생성 시도

    return []
