import os

import requests

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


class NicknameTakenError(Exception):
    pass


def _rest(path: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{path}"


def init_db() -> None:
    # 테이블은 Supabase 마이그레이션으로 미리 생성되어 있어 별도 초기화가 필요 없다.
    pass


def list_profiles() -> list[dict]:
    res = requests.get(
        _rest("profiles"),
        params={"select": "*", "order": "nickname.asc"},
        headers=_HEADERS,
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def get_profile(profile_id: int) -> dict | None:
    res = requests.get(
        _rest("profiles"),
        params={"select": "*", "id": f"eq.{profile_id}", "limit": 1},
        headers=_HEADERS,
        timeout=10,
    )
    res.raise_for_status()
    rows = res.json()
    return rows[0] if rows else None


def create_profile(nickname: str, allergies: list[str], dislikes: list[str], servings: int) -> int:
    existing = requests.get(
        _rest("profiles"),
        params={"select": "id", "nickname": f"eq.{nickname}", "limit": 1},
        headers=_HEADERS,
        timeout=10,
    )
    existing.raise_for_status()
    if existing.json():
        raise NicknameTakenError(nickname)

    res = requests.post(
        _rest("profiles"),
        json={
            "nickname": nickname,
            "allergies": ",".join(allergies),
            "dislikes": ",".join(dislikes),
            "default_servings": servings,
        },
        headers={**_HEADERS, "Prefer": "return=representation"},
        timeout=10,
    )
    res.raise_for_status()
    return res.json()[0]["id"]


def save_recipe(profile_id: int, recipe: dict) -> None:
    res = requests.post(
        _rest("saved_recipes"),
        json={
            "profile_id": profile_id,
            "title": recipe["title"],
            "time_minutes": recipe.get("time_minutes"),
            "servings": recipe.get("servings"),
            "used_ingredients": recipe.get("used_ingredients", []),
            "missing_ingredients": recipe.get("missing_ingredients", []),
            "steps": recipe.get("steps", []),
        },
        headers=_HEADERS,
        timeout=10,
    )
    res.raise_for_status()


def get_saved_recipes(profile_id: int) -> list[dict]:
    res = requests.get(
        _rest("saved_recipes"),
        params={"select": "*", "profile_id": f"eq.{profile_id}", "order": "saved_at.desc"},
        headers=_HEADERS,
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def delete_recipe(recipe_id: int) -> None:
    res = requests.delete(
        _rest("saved_recipes"),
        params={"id": f"eq.{recipe_id}"},
        headers=_HEADERS,
        timeout=10,
    )
    res.raise_for_status()
