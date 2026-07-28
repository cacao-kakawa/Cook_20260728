# 웹앱 개발 프롬프트 — 「냉장고 셰프(FridgeChef)」 3단계: 프로필·저장

### 냉장고 사진에서 재료를 인식하고 레시피를 추천하는 웹앱 | 3단계: 사용자 프로필 및 레시피 저장
### 배포 환경: Streamlit Community Cloud
### 전제: `PRD_step1.md`(재료 인식), `PRD_step2.md`(레시피 생성) 구현이 완료되어 있어야 한다

이 문서는 AI 코딩 도구(Claude Code 등)에 그대로 입력해 웹앱을 단계적으로 개발시키기 위한 **실행용 프롬프트**입니다. 그대로 복사해서 사용하세요.

---

## 0. 역할 지시 (System-level Instruction)

너는 시니어 파이썬/Streamlit 개발자다. 1~2단계에서 만든 재료 인식·레시피 생성 기능에 이어, 아래 요구사항에 따라 **사용자 프로필 생성 및 레시피 저장(마이페이지)** 기능을 추가한다.

개발은 아래 순서로 진행한다.
1) SQLite DB 스키마 설계 및 초기화 코드 작성
2) 프로필 등록/수정 페이지 구현
3) 레시피 저장(즐겨찾기) 기능 구현 — 2단계 결과 카드에 "저장하기" 버튼 연결
4) 마이페이지(저장된 레시피 목록, 프로필 관리) 구현
5) 예외처리·에러 UI

각 단계가 끝나면 결과물을 보여주고 다음 단계로 넘어가기 전 확인을 받아라.

이 문서는 3단계 중 **3단계(프로필·저장)** 만을 다룬다. 2단계 산출물(`st.session_state["recipes"]`)을 저장 대상으로 사용하며, 이 단계부터는 세션이 끝나도 데이터가 유지되도록 DB를 도입한다.

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|---|---|
| 서비스명 | 냉장고 셰프 (FridgeChef) |
| 3단계 범위 | 사용자 프로필(닉네임, 알레르기, 비선호 재료 등) 등록, 2단계에서 생성된 레시피를 즐겨찾기로 저장, 마이페이지에서 저장된 레시피·프로필 조회/관리 |
| 목표 | 세션이 끝나도(브라우저 재접속 시에도) 프로필과 저장한 레시피가 유지되도록 한다 |

---

## 2. 기술 스택

- **프레임워크**: Streamlit (Python), 기존 앱에 페이지 추가
- **데이터 저장**: `sqlite3` (Python 표준 라이브러리) — 별도 서버 없이 파일 기반 DB로 MVP 단계에 적합
  - ⚠️ **Streamlit Community Cloud 배포 시 주의**: 앱 컨테이너의 로컬 파일시스템은 재배포/재시작 시 초기화될 수 있어 SQLite 파일(`fridgechef.db`)이 유지되지 않을 수 있다. 로컬 실습·개인 사용에는 SQLite로 충분하지만, 여러 사용자가 함께 쓰는 배포본에서 데이터를 영구 보존하려면 이후 Supabase/PostgreSQL 등 외부 DB로 교체를 권장한다(본 3단계 범위 밖, 확장 옵션으로 명시만 한다)
- **상태 관리**: 로그인 없이 세션 내 "현재 프로필 ID"를 `st.session_state["profile_id"]`로 유지 (간단한 닉네임 기반 프로필 선택 방식, 별도 인증 없음)
- **API 키 보안**: 1~2단계와 동일

### 폴더 구조 예시 (3단계 반영, 최종)
```
fridgechef/
├── app.py                         # 1단계: 이미지 업로드 + 재료 인식
├── pages/
│   ├── 1_🍳_레시피_생성.py         # 2단계: 조건 입력 + 레시피 생성
│   └── 2_👤_마이페이지.py           # 3단계: 프로필 등록 + 저장된 레시피 관리
├── utils/
│   ├── vision.py                   # 1단계 비전 모델 호출 함수
│   ├── recipe.py                   # 2단계 레시피 생성 함수
│   └── db.py                       # 3단계 SQLite 연결/CRUD 함수
├── data/
│   └── fridgechef.db               # SQLite 파일 (git에는 커밋하지 않음)
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml
├── requirements.txt
└── README.md
```

---

## 3. 데이터 모델 (SQLite 스키마)

### 3-1. 테이블 정의

| 테이블 | 컬럼 | 타입 | 설명 |
|---|---|---|---|
| `profiles` | `id` | INTEGER PK AUTOINCREMENT | 프로필 ID |
| `profiles` | `nickname` | TEXT UNIQUE | 닉네임 (프로필 선택 키) |
| `profiles` | `allergies` | TEXT | 쉼표로 구분된 알레르기 재료 |
| `profiles` | `dislikes` | TEXT | 쉼표로 구분된 비선호 재료 |
| `profiles` | `default_servings` | INTEGER | 기본 인분 수 |
| `profiles` | `created_at` | TEXT | 생성 일시(ISO 문자열) |
| `saved_recipes` | `id` | INTEGER PK AUTOINCREMENT | 저장 레시피 ID |
| `saved_recipes` | `profile_id` | INTEGER FK → profiles.id | 소유 프로필 |
| `saved_recipes` | `title` | TEXT | 레시피 이름 |
| `saved_recipes` | `time_minutes` | INTEGER | 조리 시간 |
| `saved_recipes` | `servings` | INTEGER | 인분 수 |
| `saved_recipes` | `used_ingredients` | TEXT | JSON 문자열로 저장 |
| `saved_recipes` | `missing_ingredients` | TEXT | JSON 문자열로 저장 |
| `saved_recipes` | `steps` | TEXT | JSON 문자열로 저장 |
| `saved_recipes` | `saved_at` | TEXT | 저장 일시(ISO 문자열) |

### 3-2. 테이블 간 관계
| 관계 | 설명 |
|---|---|
| `saved_recipes.profile_id` → `profiles.id` | 하나의 프로필이 여러 개의 저장 레시피를 가질 수 있는 1:N 관계 |

### 3-3. `utils/db.py` 예시
```python
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/fridgechef.db")

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT UNIQUE NOT NULL,
            allergies TEXT DEFAULT '',
            dislikes TEXT DEFAULT '',
            default_servings INTEGER DEFAULT 2,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            time_minutes INTEGER,
            servings INTEGER,
            used_ingredients TEXT,
            missing_ingredients TEXT,
            steps TEXT,
            saved_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles (id)
        )
    """)
    conn.commit()
    conn.close()

def create_profile(nickname: str, allergies: list[str], dislikes: list[str], servings: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO profiles (nickname, allergies, dislikes, default_servings, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (nickname, ",".join(allergies), ",".join(dislikes), servings, datetime.utcnow().isoformat()),
    )
    conn.commit()
    profile_id = cur.lastrowid
    conn.close()
    return profile_id

def save_recipe(profile_id: int, recipe: dict) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO saved_recipes "
        "(profile_id, title, time_minutes, servings, used_ingredients, missing_ingredients, steps, saved_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            profile_id,
            recipe["title"],
            recipe.get("time_minutes"),
            recipe.get("servings"),
            json.dumps(recipe.get("used_ingredients", []), ensure_ascii=False),
            json.dumps(recipe.get("missing_ingredients", []), ensure_ascii=False),
            json.dumps(recipe.get("steps", []), ensure_ascii=False),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

def get_saved_recipes(profile_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM saved_recipes WHERE profile_id = ? ORDER BY saved_at DESC", (profile_id,)
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "time_minutes": r["time_minutes"],
            "servings": r["servings"],
            "used_ingredients": json.loads(r["used_ingredients"] or "[]"),
            "missing_ingredients": json.loads(r["missing_ingredients"] or "[]"),
            "steps": json.loads(r["steps"] or "[]"),
            "saved_at": r["saved_at"],
        }
        for r in rows
    ]

def delete_recipe(recipe_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM saved_recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
```

---

## 4. 화면별 상세 요구사항

### 4-1. 프로필 등록/선택 (마이페이지 상단, `pages/2_👤_마이페이지.py`)
- 앱 최초 진입 시 `init_db()`를 1회 호출해 테이블이 없으면 생성
- 닉네임으로 기존 프로필 선택(`st.selectbox`) 또는 "새 프로필 만들기" 폼(`st.form`) 제공
  - 입력 항목: 닉네임(`st.text_input`), 알레르기 재료(`st.text_input`, 쉼표 구분 또는 `st.multiselect`), 비선호 재료(동일), 기본 인분 수(`st.number_input`)
- 선택/생성된 프로필의 `id`를 `st.session_state["profile_id"]`, 닉네임을 `st.session_state["profile_nickname"]`에 저장
- 2단계 레시피 생성 페이지에서는 프로필이 선택되어 있으면 알레르기/비선호 재료를 조건 입력의 기본값으로 자동 채운다

### 4-2. 레시피 저장 연결 (2단계 화면 수정)
- `pages/1_🍳_레시피_생성.py`의 각 레시피 카드 "저장하기" 버튼을 활성화한다
- 프로필이 선택되어 있지 않으면 버튼 클릭 시 "먼저 마이페이지에서 프로필을 만들어주세요" 안내와 함께 마이페이지로 이동하는 버튼 제공
- 프로필이 있으면 `save_recipe(profile_id, recipe)` 호출 후 `st.toast` 또는 `st.success`로 "레시피를 저장했습니다" 안내

### 4-3. 저장된 레시피 목록 (마이페이지 하단)
- `get_saved_recipes(profile_id)`로 조회해 카드 형태로 표시(2단계와 동일한 카드 UI 재사용)
- 각 카드에 "삭제" 버튼 제공 → `delete_recipe(recipe_id)` 호출 후 목록 새로고침(`st.rerun`)
- 저장 일시 기준 최신순 정렬, 목록이 비어있으면 "아직 저장한 레시피가 없어요" 안내

---

## 5. 예외처리 및 데이터 신뢰성 원칙

- DB 파일/테이블이 없는 최초 실행 상태를 항상 처리한다(`init_db()`를 앱 시작 시 idempotent하게 호출)
- 닉네임 중복 등록 시 `sqlite3.IntegrityError`를 잡아 `st.error`로 "이미 존재하는 닉네임입니다"를 안내
- 프로필 없이 저장/조회를 시도하는 모든 경로를 가드한다
- Streamlit Community Cloud 배포 시 SQLite 파일이 재시작 후 사라질 수 있다는 점을 마이페이지 하단에 `st.caption`으로 고지한다("본 서비스는 로컬 실행 기준으로 데이터가 유지됩니다. 배포 환경에서는 재시작 시 초기화될 수 있습니다.")
- 삭제는 확인 없이 즉시 반영하지 않고, `st.button`에 고유 key를 부여해 실수 클릭으로 인한 중복 삭제 호출을 방지한다

---

## 6. 디자인 가이드 (1~2단계 테마 유지)

1~2단계의 `.streamlit/config.toml` 테마를 그대로 유지한다. 마이페이지는 프로필 카드(상단)와 저장된 레시피 카드 그리드(하단)로 구성해 정보 위계를 분리한다.

---

## 7. 수용 기준 (Acceptance Criteria)

- [ ] 최초 실행 시 `profiles`, `saved_recipes` 테이블이 자동 생성된다
- [ ] 닉네임/알레르기/비선호 재료/기본 인분 수로 새 프로필을 만들 수 있다
- [ ] 기존 프로필을 선택해 `st.session_state["profile_id"]`로 유지할 수 있다
- [ ] 2단계에서 생성한 레시피를 "저장하기" 버튼으로 DB에 저장할 수 있다
- [ ] 마이페이지에서 저장된 레시피 목록을 조회하고 개별 삭제할 수 있다
- [ ] 프로필 없이 저장을 시도하면 안내 후 마이페이지로 유도한다
- [ ] 닉네임 중복, DB 오류 등 예외 상황에서 앱이 죽지 않고 안내 메시지를 표시한다
- [ ] SQLite 파일이 git에 커밋되지 않도록 `.gitignore`에 `data/*.db`가 포함되어 있다

---

## 8. requirements.txt (최종, 1~3단계 누적)
```
streamlit
openai
pillow
python-dotenv
```
> `sqlite3`는 Python 표준 라이브러리이므로 `requirements.txt`에 별도 명시하지 않는다.

---


**사용 방법**: `PRD_step1.md`, `PRD_step2.md`로 1~2단계가 완료된 상태에서, 이 프롬프트 전체를 Claude Code에 붙여넣고 "3단계(프로필·저장)부터 시작해줘"라고 요청하세요. 3단계까지 완료되면 냉장고 셰프 MVP가 완성됩니다.


## 9. 기술스택 python, flask