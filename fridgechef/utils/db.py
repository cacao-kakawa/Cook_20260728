import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Vercel의 서버리스 환경은 배포 파일시스템이 읽기 전용이라 /tmp만 쓰기 가능하다.
# 이 경우 데이터는 함수 인스턴스가 재시작될 때마다 초기화된다(PRD_step3.md의 배포 caveat 참고).
if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/fridgechef.db")
else:
    DB_PATH = Path(
        os.environ.get("FRIDGECHEF_DB_PATH")
        or (Path(__file__).resolve().parent.parent / "data" / "fridgechef.db")
    )


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
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
    finally:
        conn.close()


def list_profiles() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM profiles ORDER BY nickname").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_profile(profile_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_profile(nickname: str, allergies: list[str], dislikes: list[str], servings: int) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO profiles (nickname, allergies, dislikes, default_servings, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (nickname, ",".join(allergies), ",".join(dislikes), servings, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def save_recipe(profile_id: int, recipe: dict) -> None:
    conn = get_connection()
    try:
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
    finally:
        conn.close()


def get_saved_recipes(profile_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM saved_recipes WHERE profile_id = ? ORDER BY saved_at DESC", (profile_id,)
        ).fetchall()
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
    finally:
        conn.close()


def delete_recipe(recipe_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM saved_recipes WHERE id = ?", (recipe_id,))
        conn.commit()
    finally:
        conn.close()
