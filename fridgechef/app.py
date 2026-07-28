import os

from flask import Flask, flash, redirect, render_template, request, session, url_for

from utils.db import (
    NicknameTakenError,
    create_profile,
    delete_recipe,
    get_profile,
    get_saved_recipes,
    init_db,
    list_profiles,
    save_recipe,
)
from utils.recipe import generate_recipes
from utils.vision import recognize_ingredients

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

init_db()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _current_profile() -> dict | None:
    profile_id = session.get("profile_id")
    return get_profile(profile_id) if profile_id else None


def _recipe_condition_defaults() -> tuple[str, int]:
    profile = _current_profile()
    if not profile:
        return "", 2
    excluded = [x for x in (profile["allergies"] + "," + profile["dislikes"]).split(",") if x]
    return ", ".join(excluded), profile["default_servings"] or 2


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", ingredients=session.get("ingredients", []), error=None)


@app.route("/recognize", methods=["POST"])
def recognize():
    file = request.files.get("image")

    if not file or file.filename == "":
        return render_template(
            "index.html", ingredients=session.get("ingredients", []),
            error="이미지를 업로드해주세요.",
        )

    if not _allowed_file(file.filename):
        return render_template(
            "index.html", ingredients=session.get("ingredients", []),
            error="jpg, jpeg, png 형식의 이미지만 업로드할 수 있습니다.",
        )

    try:
        ingredients = recognize_ingredients(file.read())
    except Exception:
        return render_template(
            "index.html", ingredients=session.get("ingredients", []),
            error="재료 인식에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )

    if not ingredients:
        return render_template(
            "index.html", ingredients=[],
            error="재료를 인식하지 못했습니다. 사진을 다시 찍어주세요.",
        )

    session["ingredients"] = ingredients
    return render_template("index.html", ingredients=ingredients, error=None)


@app.route("/ingredients/add", methods=["POST"])
def add_ingredient():
    new_item = request.form.get("new_ingredient", "").strip()
    ingredients = session.get("ingredients", [])
    if new_item and new_item not in ingredients:
        ingredients.append(new_item)
        session["ingredients"] = ingredients
    return render_template("index.html", ingredients=ingredients, error=None)


@app.route("/ingredients/remove", methods=["POST"])
def remove_ingredient():
    target = request.form.get("target")
    ingredients = [i for i in session.get("ingredients", []) if i != target]
    session["ingredients"] = ingredients
    return render_template("index.html", ingredients=ingredients, error=None)


@app.route("/recipes", methods=["GET"])
def recipes_page():
    default_exclude, default_servings = _recipe_condition_defaults()
    return render_template(
        "recipes.html",
        ingredients=session.get("ingredients", []),
        recipes=session.get("recipes", []),
        error=None,
        profile_id=session.get("profile_id"),
        default_exclude=default_exclude,
        default_servings=default_servings,
    )


@app.route("/recipes/generate", methods=["POST"])
def recipes_generate():
    ingredients = session.get("ingredients", [])
    default_exclude, default_servings = _recipe_condition_defaults()
    common = dict(
        ingredients=ingredients,
        profile_id=session.get("profile_id"),
        default_exclude=default_exclude,
        default_servings=default_servings,
    )

    if not ingredients:
        return render_template("recipes.html", recipes=[], error=None, **common)

    servings = request.form.get("servings", type=int) or 2
    max_time_minutes = request.form.get("max_time_minutes", type=int)
    exclude_raw = request.form.get("exclude", "")
    exclude = [x.strip() for x in exclude_raw.split(",") if x.strip()]

    try:
        recipes = generate_recipes(
            ingredients,
            servings=servings,
            max_time_minutes=max_time_minutes,
            exclude=exclude,
        )
    except Exception:
        return render_template(
            "recipes.html", recipes=[],
            error="레시피 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
            **common,
        )

    if not recipes:
        return render_template(
            "recipes.html", recipes=[],
            error="레시피를 생성하지 못했습니다. 다시 시도해주세요.",
            **common,
        )

    for recipe in recipes:
        text = " ".join(recipe.get("used_ingredients", []) + recipe.get("steps", []))
        recipe["warning"] = any(item in text for item in exclude)

    session["recipes"] = recipes
    return render_template("recipes.html", recipes=recipes, error=None, **common)


@app.route("/recipes/save/<int:index>", methods=["POST"])
def recipes_save(index):
    profile_id = session.get("profile_id")
    if not profile_id:
        flash("먼저 마이페이지에서 프로필을 만들어주세요.")
        return redirect(url_for("profile_page"))

    recipes = session.get("recipes", [])
    if 0 <= index < len(recipes):
        try:
            save_recipe(profile_id, recipes[index])
            flash(f"'{recipes[index]['title']}' 레시피를 저장했습니다.")
        except Exception:
            flash("레시피 저장에 실패했습니다. 잠시 후 다시 시도해주세요.")
    return redirect(url_for("recipes_page"))


@app.route("/profile", methods=["GET"])
def profile_page():
    profile_id = session.get("profile_id")
    saved_recipes = get_saved_recipes(profile_id) if profile_id else []
    return render_template(
        "profile.html",
        profiles=list_profiles(),
        profile_id=profile_id,
        profile_nickname=session.get("profile_nickname"),
        saved_recipes=saved_recipes,
    )


@app.route("/profile/create", methods=["POST"])
def profile_create():
    nickname = request.form.get("nickname", "").strip()
    allergies = [x.strip() for x in request.form.get("allergies", "").split(",") if x.strip()]
    dislikes = [x.strip() for x in request.form.get("dislikes", "").split(",") if x.strip()]
    default_servings = request.form.get("default_servings", type=int) or 2

    if not nickname:
        flash("닉네임을 입력해주세요.")
        return redirect(url_for("profile_page"))

    try:
        profile_id = create_profile(nickname, allergies, dislikes, default_servings)
    except NicknameTakenError:
        flash("이미 존재하는 닉네임입니다.")
        return redirect(url_for("profile_page"))

    session["profile_id"] = profile_id
    session["profile_nickname"] = nickname
    flash(f"'{nickname}' 프로필을 생성했습니다.")
    return redirect(url_for("profile_page"))


@app.route("/profile/select", methods=["POST"])
def profile_select():
    profile_id = request.form.get("profile_id", type=int)
    profile = get_profile(profile_id) if profile_id else None
    if not profile:
        flash("프로필을 찾을 수 없습니다.")
        return redirect(url_for("profile_page"))

    session["profile_id"] = profile["id"]
    session["profile_nickname"] = profile["nickname"]
    return redirect(url_for("profile_page"))


@app.route("/profile/recipes/delete", methods=["POST"])
def profile_recipe_delete():
    recipe_id = request.form.get("recipe_id", type=int)
    if recipe_id:
        delete_recipe(recipe_id)
    return redirect(url_for("profile_page"))


if __name__ == "__main__":
    app.run(debug=True)
