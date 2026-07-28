# 웹앱 개발 프롬프트 — 「냉장고 셰프(FridgeChef)」 2단계: 레시피 생성

### 냉장고 사진에서 재료를 인식하고 레시피를 추천하는 웹앱 | 2단계: 레시피 생성
### 배포 환경: Streamlit Community Cloud
### 전제: `PRD_step1.md` 기반 1단계(재료 인식) 구현이 완료되어 있어야 한다

이 문서는 AI 코딩 도구(Claude Code 등)에 그대로 입력해 웹앱을 단계적으로 개발시키기 위한 **실행용 프롬프트**입니다. 그대로 복사해서 사용하세요.

---

## 0. 역할 지시 (System-level Instruction)

너는 시니어 파이썬/Streamlit 개발자다. 1단계에서 만든 재료 인식 기능(`st.session_state["ingredients"]`)에 이어, 아래 요구사항에 따라 **레시피 생성 페이지**를 추가한다.

개발은 아래 순서로 진행한다.
1) 레시피 생성 페이지 레이아웃(재료 확인, 조건 입력 위젯, 결과 카드) 작성
2) OpenRouter API(`openai/gpt-oss-20b:free`) 연동 및 재료 → 레시피 생성 기능 구현
3) 레시피 결과를 카드 형태 UI로 렌더링
4) 예외처리·에러 UI·로딩 상태 표시

각 단계가 끝나면 결과물을 보여주고 다음 단계로 넘어가기 전 확인을 받아라.

이 문서는 3단계 중 **2단계(레시피 생성)** 만을 다룬다. 1단계 산출물(인식된 재료 목록)을 입력으로 받아 레시피를 생성하며, 2단계 산출물(생성된 레시피)은 3단계(`PRD_step3.md`, 프로필·저장)에서 저장 대상이 된다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | 냉장고 셰프 (FridgeChef) |
| 2단계 범위 | 1단계에서 인식된 재료 목록 + 사용자 조건(인분 수, 조리 시간, 알레르기/비선호 재료 등)을 받아 텍스트 생성 모델로 레시피 2~3개를 생성하고 카드 형태로 표시 |
| 입력 | `st.session_state["ingredients"]` (1단계 산출물), 사용자가 입력하는 부가 조건 |
| 출력 | 레시피명, 조리 시간, 사용 재료/부족한 재료, 조리 순서가 포함된 레시피 카드 |

---

## 2. 기술 스택

- **프레임워크**: Streamlit (Python), 1단계와 동일 앱에 페이지 추가 (`pages/1_레시피_생성.py`)
- **AI API**: OpenRouter (`https://openrouter.ai/api/v1`), `openai` SDK
  - 레시피 생성 모델: `openai/gpt-oss-20b:free`
- **상태 관리**: `st.session_state["ingredients"]`(1단계에서 전달), `st.session_state["recipes"]`(2단계 결과, 3단계에서 저장 대상으로 사용)
- **API 키 보안**: 1단계와 동일하게 `.streamlit/secrets.toml`의 `OPENROUTER_API_KEY` 사용

### 폴더 구조 예시 (2단계 반영)
```
fridgechef/
├── app.py                         # 1단계: 이미지 업로드 + 재료 인식
├── pages/
│   └── 1_🍳_레시피_생성.py         # 2단계: 조건 입력 + 레시피 생성
├── utils/
│   ├── vision.py                   # 1단계 비전 모델 호출 함수
│   └── recipe.py                   # 2단계 레시피 생성 함수
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml
├── requirements.txt
└── README.md
```

---

## 3. OpenRouter 텍스트 생성 API 연동 상세 명세

### 3-1. 호출 방식
1단계와 동일하게 `openai` SDK를 OpenRouter `base_url`로 사용하되, 모델만 텍스트 생성 모델(`openai/gpt-oss-20b:free`)로 교체한다. 이미지 입력 없이 텍스트만 주고받는다.

- **모델**: `openai/gpt-oss-20b:free`
- **입력**: 인식된 재료 목록 + 사용자 조건(인분 수, 최대 조리 시간, 알레르기/비선호 재료, 선호 요리 종류 등)
- **출력**: 레시피 2~3개를 담은 JSON (레시피명, 조리시간, 사용 재료, 부족한 재료, 조리 순서)

### 3-2. 프롬프트 설계
2단계 이후 카드 UI 렌더링과 3단계 저장을 위해, **반드시 JSON 형식으로만** 응답하도록 지시한다.

```text
당신은 냉장고 속 재료를 활용한 레시피를 추천하는 요리 어시스턴트입니다.
아래 조건에 맞는 레시피를 2~3개 추천하고, 반드시 아래 JSON 형식으로만 답하세요.
다른 설명 문장은 절대 포함하지 마세요.

{
  "recipes": [
    {
      "title": "레시피 이름",
      "time_minutes": 20,
      "servings": 2,
      "used_ingredients": ["보유 재료 중 사용하는 것들"],
      "missing_ingredients": ["추가로 필요한 재료(없으면 빈 배열)"],
      "steps": ["조리 순서 1", "조리 순서 2", "..."]
    }
  ]
}
```

### 3-3. 호출 예시 (`utils/recipe.py`)
```python
import json
from openai import OpenAI
import streamlit as st

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"],
)

RECIPE_MODEL = "openai/gpt-oss-20b:free"

SYSTEM_PROMPT = (
    "당신은 냉장고 속 재료를 활용한 레시피를 추천하는 요리 어시스턴트입니다. "
    "반드시 JSON 형식으로만 답하고, 다른 설명 문장은 포함하지 마세요. "
    '형식: {"recipes": [{"title": str, "time_minutes": int, "servings": int, '
    '"used_ingredients": [str], "missing_ingredients": [str], "steps": [str]}]}'
)

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

    response = client.chat.completions.create(
        model=RECIPE_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        return data.get("recipes", [])
    except json.JSONDecodeError:
        return []
```

---

## 4. 데이터 모델 (`session_state` 저장 예시)

```python
# st.session_state["recipes"] 에 리스트 형태로 저장 (3단계에서 그대로 저장 대상으로 사용)
{
    "title": "두부김치찌개",
    "time_minutes": 20,
    "servings": 2,
    "used_ingredients": ["두부", "김치", "대파"],
    "missing_ingredients": ["돼지고기(선택)"],
    "steps": ["냄비에 김치와 물을 넣고 끓인다.", "두부와 대파를 넣고 5분 더 끓인다."],
}
```
- 3단계에서 이 구조를 그대로 SQLite 테이블 스키마(`saved_recipes`)로 옮겨 영구 저장한다.

---

## 5. 화면별 상세 요구사항 (`pages/1_🍳_레시피_생성.py`)

- 페이지 진입 시 `st.session_state["ingredients"]`가 없으면 "먼저 1단계에서 냉장고 사진을 인식해주세요"를 안내하고 1단계 페이지로 돌아가는 버튼(`st.switch_page`)을 제공
- 인식된 재료 목록을 상단에 배지/태그로 다시 보여준다 (확인용)
- 조건 입력 위젯:
  - `st.number_input` 또는 `st.slider`: 인분 수 (기본값 2)
  - `st.slider`: 최대 조리 시간(분, 선택 사항)
  - `st.multiselect` 또는 `st.text_input`: 알레르기/비선호 재료 제외 목록
- "레시피 추천받기" 버튼 클릭 시 `st.spinner("레시피를 고민하는 중...")` 표시 후 `generate_recipes()` 호출
- 결과를 `st.session_state["recipes"]`에 저장하고, 레시피별로 `st.expander` 또는 `st.columns` 카드 형태로 표시:
  - 레시피명(제목), 예상 조리 시간, 인분 수
  - 사용하는 재료 vs 추가로 필요한 재료를 구분해서 표시(배지 색상 다르게)
  - 조리 순서를 번호 목록(`st.markdown`)으로 표시
- 각 레시피 카드 하단에 "이 레시피 저장하기" 버튼을 두되, 3단계에서 실제 저장 기능을 구현하기 전까지는 버튼을 비활성화하거나 "3단계에서 구현 예정" 안내로 대체

---

## 6. 예외처리 및 데이터 신뢰성 원칙

- 1단계에서 인식된 재료가 없는 상태로 2단계에 진입할 수 없도록 가드한다
- OpenRouter API 호출 실패 시 `st.error`로 "레시피 생성에 실패했습니다. 잠시 후 다시 시도해주세요" 안내 + 재시도 버튼
- 무료 모델의 rate limit(429) 대응을 위한 1회 자동 재시도 로직 포함
- 모델 응답이 JSON 파싱에 실패하면 빈 리스트를 반환하고, 화면에는 "레시피를 생성하지 못했습니다. 다시 시도해주세요"를 안내(추천 결과가 아예 없는 것으로 처리하며, 임의로 지어낸 레시피를 표시하지 않는다)
- 사용자가 제외 요청한 알레르기/비선호 재료가 레시피에 포함되지 않았는지 화면 표시 전 간단히 검증(포함되어 있으면 경고 배지 표시)

---

## 7. 디자인 가이드 (1단계 테마 유지)

1단계의 `.streamlit/config.toml` 테마를 그대로 유지한다.
- 사용 재료는 그린 계열 배지, 추가로 필요한 재료는 옐로/오렌지 계열 배지로 구분해 시각적으로 구별한다

---

## 8. 수용 기준 (Acceptance Criteria)

- [ ] 1단계 인식 결과 없이 2단계 페이지에 접근하면 안내 후 1단계로 유도한다
- [ ] 인분 수, 조리 시간, 제외 재료 등 조건을 입력할 수 있다
- [ ] "레시피 추천받기" 클릭 시 `openai/gpt-oss-20b:free` 모델을 호출해 레시피 2~3개를 생성한다
- [ ] 생성된 레시피가 제목/시간/인분/사용 재료/부족 재료/조리 순서를 포함한 카드로 표시된다
- [ ] 결과가 `st.session_state["recipes"]`에 저장되어 3단계에서 이어받을 수 있다
- [ ] API 오류, JSON 파싱 실패 등 예외 상황에서 앱이 죽지 않고 안내 메시지를 표시한다
- [ ] 사용자가 제외 요청한 재료가 레시피에 포함되면 경고가 표시된다

---

## 9. requirements.txt (2단계까지 누적)
```
streamlit
openai
pillow
python-dotenv
```

---

**사용 방법**: `PRD_step1.md`로 1단계가 완료된 상태에서, 이 프롬프트 전체를 Claude Code에 붙여넣고 "2단계(레시피 생성)부터 시작해줘"라고 요청하세요. 완료 후 `PRD_step3.md`로 이어서 진행합니다.


## 10. 기술스택 python, flask