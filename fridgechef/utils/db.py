import os

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

_client = None


class NicknameTakenError(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def init_db() -> None:
    # 테이블은 Supabase 마이그레이션으로 미리 생성되어 있어 별도 초기화가 필요 없다.
    pass


def list_profiles() -> list[dict]:
    res = _get_client().table("profiles").select("*").order("nickname").execute()
    return res.data


def get_profile(profile_id: int) -> dict | None:
    res = _get_client().table("profiles").select("*").eq("id", profile_id).limit(1).execute()
    return res.data[0] if res.data else None


def create_profile(nickname: str, allergies: list[str], dislikes: list[str], servings: int) -> int:
    client = _get_client()
    existing = client.table("profiles").select("id").eq("nickname", nickname).limit(1).execute()
    if existing.data:
        raise NicknameTakenError(nickname)

    res = client.table("profiles").insert({
        "nickname": nickname,
        "allergies": ",".join(allergies),
        "dislikes": ",".join(dislikes),
        "default_servings": servings,
    }).execute()
    return res.data[0]["id"]


def save_recipe(profile_id: int, recipe: dict) -> None:
    _get_client().table("saved_recipes").insert({
        "profile_id": profile_id,
        "title": recipe["title"],
        "time_minutes": recipe.get("time_minutes"),
        "servings": recipe.get("servings"),
        "used_ingredients": recipe.get("used_ingredients", []),
        "missing_ingredients": recipe.get("missing_ingredients", []),
        "steps": recipe.get("steps", []),
    }).execute()


def get_saved_recipes(profile_id: int) -> list[dict]:
    res = (
        _get_client()
        .table("saved_recipes")
        .select("*")
        .eq("profile_id", profile_id)
        .order("saved_at", desc=True)
        .execute()
    )
    return res.data


def delete_recipe(recipe_id: int) -> None:
    _get_client().table("saved_recipes").delete().eq("id", recipe_id).execute()
