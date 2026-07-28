# 웹앱 개발 프롬프트 — 「냉장고 셰프(FridgeChef)」 1단계: 이미지 인식

### 냉장고 사진에서 재료를 인식하고 레시피를 추천하는 웹앱 | 1단계: 재료 인식
### 배포 환경: Streamlit Community Cloud

이 문서는 AI 코딩 도구(Claude Code 등)에 그대로 입력해 웹앱을 단계적으로 개발시키기 위한 **실행용 프롬프트**입니다. 그대로 복사해서 사용하세요.

---

## 0. 역할 지시 (System-level Instruction)

너는 시니어 파이썬/Streamlit 개발자다. 아래 요구사항에 따라 **Streamlit** 기반 웹앱의 1단계(냉장고 사진 업로드 → 재료 인식)를 만든다. **Streamlit Community Cloud 무료 티어**에 바로 배포 가능한 구조(단일 GitHub 저장소 + `requirements.txt` + `.streamlit/secrets.toml`)로 작성한다.

개발은 아래 순서로 진행한다.
1) 랜딩 페이지 레이아웃(이미지 업로드 위젯, 안내 문구) 작성
2) `.streamlit/config.toml`을 이용한 테마(색상/폰트) 적용
3) OpenRouter API(`google/gemma-4-26b-a4b-it:free`) 연동 및 이미지 → 재료 인식 기능 구현
4) 예외처리·에러 UI·로딩 상태 표시

각 단계가 끝나면 결과물을 보여주고 다음 단계로 넘어가기 전 확인을 받아라.

전체 서비스는 3단계로 나뉘며, 이 문서는 **1단계(이미지 인식)** 만을 다룬다. 2단계(레시피 생성), 3단계(프로필·저장)는 각각 `PRD_step2.md`, `PRD_step3.md`에서 별도로 진행한다. 1단계 산출물(`st.session_state["ingredients"]`)은 2단계 입력으로 그대로 이어진다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | 냉장고 셰프 (FridgeChef) |
| 한 줄 정의 | 냉장고 사진 한 장으로 보유 식재료를 자동 인식하고, 그 재료로 만들 수 있는 레시피를 추천해주는 서비스 |
| 해결하는 문제 | 냉장고에 뭐가 있는지는 알지만 무엇을 해먹을지 몰라 배달·외식으로 이어지거나 식재료를 방치해 버리게 되는 문제 |
| 핵심 타깃 | 자취생, 맞벌이 가정 등 매 끼니 메뉴 고민이 부담스러운 1인 가구·가정 요리 초보자 |
| 1단계 범위 | 냉장고 사진 업로드 → 비전 모델로 식재료 목록 추출 → 화면에 목록 표시 및 세션 저장 |

---

## 2. 기술 스택

- **프레임워크**: Streamlit (Python)
- **AI API**: OpenRouter (`https://openrouter.ai/api/v1`), OpenAI 호환 SDK(`openai` 파이썬 패키지) 사용
  - 이미지 인식 모델: `google/gemma-4-26b-a4b-it:free`
- **이미지 처리**: `Pillow` — 업로드된 이미지를 리사이즈/JPEG 압축 후 base64 인코딩(무료 모델의 요청 크기·토큰 제한을 고려해 긴 변 1024px 이하로 축소 권장)
- **상태 관리**: `st.session_state` — 인식된 재료 목록을 2단계에서 이어받을 수 있도록 저장
- **API 키 보안**: `.streamlit/secrets.toml`에 `OPENROUTER_API_KEY` 저장 (로컬 개발 시 `.env` + `python-dotenv`도 병행 가능하되, 배포본 코드는 `st.secrets` 우선 참조. 코드에는 절대 하드코딩하지 않음)

### 폴더 구조 예시 (1단계 기준)
```
fridgechef/
├── app.py                     # 랜딩 페이지 (이미지 업로드 + 재료 인식)
├── utils/
│   └── vision.py               # OpenRouter 비전 모델 호출 함수
├── .streamlit/
│   ├── config.toml             # 테마 설정
│   └── secrets.toml             # API 키 (로컬 전용, git에는 커밋하지 않음)
├── requirements.txt
└── README.md
```

---

## 3. OpenRouter 비전 API 연동 상세 명세

### 3-1. 호출 방식
OpenRouter는 OpenAI 호환 API이므로 `openai` 파이썬 SDK의 `base_url`만 교체해서 사용한다. 이미지는 `data:` base64 URI 형태로 `image_url` content로 전달한다.

- **Endpoint**: `https://openrouter.ai/api/v1/chat/completions` (SDK를 통해 호출)
- **모델**: `google/gemma-4-26b-a4b-it:free`
- **입력**: 텍스트 프롬프트 + base64 인코딩된 냉장고 사진 1장
- **출력**: 인식된 식재료 이름의 JSON 배열(예: `["계란", "대파", "두부", "김치"]`)

### 3-2. 프롬프트 설계
모델이 자유 서술형으로 답하면 2단계에서 파싱하기 어려우므로, **반드시 JSON 배열만 출력**하도록 지시하고 파싱 실패에 대비한 fallback을 둔다.

```text
당신은 냉장고 사진에서 식재료를 인식하는 비전 어시스턴트입니다.
이미지에 보이는 식재료(채소, 육류, 유제품, 소스류, 반찬 등)의 이름만 한국어로,
다른 설명 없이 JSON 배열 형태로만 답하세요.
예시: ["계란", "대파", "두부", "김치"]
포장지 문구나 브랜드명은 제외하고 식재료 종류만 나열하세요.
```

### 3-3. 호출 예시 (`utils/vision.py`)
```python
import base64
import json
import io
from openai import OpenAI
from PIL import Image
import streamlit as st

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"],
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
    try:
        ingredients = json.loads(raw)
        if isinstance(ingredients, list):
            return [str(i).strip() for i in ingredients if str(i).strip()]
    except json.JSONDecodeError:
        pass
    # fallback: JSON 파싱 실패 시 줄 단위/쉼표 단위로 재시도
    fallback = [s.strip(" -•\"'[]") for s in raw.replace(",", "\n").splitlines()]
    return [s for s in fallback if s]
```

`secrets.toml` 예시:
```toml
OPENROUTER_API_KEY = "sk-or-v1-..."
```

---

## 4. 화면별 상세 요구사항 (`app.py`)

- `st.title` + 서비스 한 줄 소개
- `st.file_uploader`로 이미지 업로드 (jpg, jpeg, png 허용, 1개 파일)
- 업로드 즉시 `st.image`로 미리보기 표시
- "재료 인식하기" 버튼 클릭 시 `st.spinner("냉장고를 살펴보는 중...")` 표시 후 `recognize_ingredients()` 호출
- 인식 결과를 `st.session_state["ingredients"]`에 저장하고, 재료 목록을 `st.chip`/`st.multiselect` 또는 태그형 배지(`st.markdown` HTML)로 표시
- 인식된 재료 목록을 **사용자가 직접 수정 가능**하게 한다 (오인식 보정): `st.multiselect`의 기본 선택값으로 인식 결과를 넣고, 옵션에 자유 추가 가능하도록 `st.text_input`으로 재료 수동 추가 기능 제공
- 하단에 "이 재료로 레시피 추천받기 →" 버튼을 두되, 1단계에서는 페이지 전환 없이 버튼 비활성화 상태(또는 "2단계에서 구현 예정" 안내)로 두거나, `st.switch_page`로 2단계 페이지 이동을 준비만 해둔다

---

## 5. 예외처리 및 데이터 신뢰성 원칙

- 이미지를 업로드하지 않고 "재료 인식하기"를 누르면 `st.warning`으로 안내하고 API를 호출하지 않는다
- OpenRouter API 호출 실패(rate limit, timeout, 네트워크 오류 등 `openai.APIError` 계열 예외) 시 `st.error`로 "재료 인식에 실패했습니다. 잠시 후 다시 시도해주세요" 안내 + 재시도 버튼
- 무료 모델은 요청량이 몰리면 429(rate limit) 응답이 올 수 있으므로, 1회 자동 재시도(짧은 대기 후) 로직을 넣는다
- 모델 응답이 JSON 형식이 아니어도 fallback 파싱으로 최대한 목록을 추출하고, 그래도 빈 목록이면 "재료를 인식하지 못했습니다. 사진을 다시 찍어주세요"를 안내한다
- 업로드 이미지 용량이 클 경우 리사이즈를 반드시 거쳐 base64 페이로드 크기를 줄인다 (권장: 긴 변 1024px, JPEG 품질 85)

---

## 6. 디자인 가이드 (제안)

`.streamlit/config.toml`:
```toml
[theme]
primaryColor="#3DA35D"          # 포인트 컬러(신선한 그린)
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F4F9F1"
textColor="#2B2B2B"
font="sans serif"
```
- 톤: 신선하고 건강한 느낌의 그린 계열 + 화이트 배경
- 인식된 재료는 태그/배지 형태로 시각적으로 한눈에 보이게 표시

---

## 7. 수용 기준 (Acceptance Criteria)

- [ ] 이미지를 업로드하면 미리보기가 표시된다
- [ ] "재료 인식하기" 버튼 클릭 시 `google/gemma-4-26b-a4b-it:free` 모델을 호출해 재료 목록을 반환한다
- [ ] 인식 결과가 `st.session_state["ingredients"]`에 저장되어 2단계에서 이어받을 수 있다
- [ ] 사용자가 인식된 재료 목록을 직접 추가/삭제(보정)할 수 있다
- [ ] 이미지 미업로드, API 오류, 파싱 실패 등 예외 상황에서 앱이 죽지 않고 안내 메시지를 표시한다
- [ ] API 키가 코드에 하드코딩되지 않고 `st.secrets`(또는 `.env`)로만 참조된다
- [ ] `requirements.txt`가 정확하고 Streamlit Community Cloud에 무료로 배포 가능하다

---

## 8. requirements.txt (1단계 기준)
```
streamlit
openai
pillow
python-dotenv
```

---

**사용 방법**: 이 프롬프트 전체를 Claude Code(또는 다른 AI 코딩 도구)에 붙여넣고 "1단계(이미지 업로드 + 재료 인식)부터 시작해줘"라고 요청하세요. 완료 후 `PRD_step2.md`로 이어서 진행합니다.


## 9. 기술스택 python, flask