import html
import json
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


class RecipeParseError(Exception):
    pass


def to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return html.unescape(value).strip()
    if isinstance(value, list):
        parts = [to_text(item) for item in value]
        return ", ".join([part for part in parts if part])
    if isinstance(value, (int, float, bool)):
        return str(value)
    return html.unescape(str(value)).strip()


def normalize_step_text(text: str) -> str:
    clean = to_text(text)
    clean = re.sub(
        r"^\s*(?:schritt|step)\s*\d+\s*[:.)-]?\s*",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"^\s*\d+\s*[:.)-]\s*", "", clean)
    return clean.strip()


def normalize_type(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.lower()]
    if isinstance(value, list):
        return [str(v).lower() for v in value]
    return []


def iter_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from iter_dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_dicts(item)


def extract_recipe_candidates(obj: Any) -> list[dict[str, Any]]:
    recipes: list[dict[str, Any]] = []
    for node in iter_dicts(obj):
        node_types = normalize_type(node.get("@type"))
        if any("recipe" == t or t.endswith("recipe") for t in node_types):
            recipes.append(node)
    return recipes


def parse_instruction_node(node: Any) -> list[str]:
    steps: list[str] = []
    if isinstance(node, str):
        clean = normalize_step_text(node)
        if clean:
            steps.append(clean)
        return steps

    if isinstance(node, list):
        for item in node:
            steps.extend(parse_instruction_node(item))
        return steps

    if isinstance(node, dict):
        text = node.get("text")
        if not isinstance(text, str):
            text = node.get("description")
        if isinstance(text, str):
            clean = normalize_step_text(text)
            if clean:
                steps.append(clean)
        if "itemListElement" in node:
            steps.extend(parse_instruction_node(node["itemListElement"]))
    return steps


def parse_nutrition(nutrition: Any) -> list[dict[str, str]]:
    if not isinstance(nutrition, dict):
        return []
    values: list[dict[str, str]] = []
    for key, value in nutrition.items():
        if key.startswith("@"):
            continue
        if value in (None, ""):
            continue
        label = re.sub(r"([a-z])([A-Z])", r"\1 \2", key).strip()
        values.append({"label": label.title(), "value": to_text(value)})
    return values


def get_first(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return to_text(value[0])
    if isinstance(value, str):
        return to_text(value)
    return None


def select_best_recipe(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda recipe: len(parse_instruction_node(recipe.get("recipeInstructions")))
        + len(recipe.get("recipeIngredient", []) if isinstance(recipe.get("recipeIngredient"), list) else []),
    )


def extract_recipe_from_html(html_text: str, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html_text, "html.parser")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    recipe_candidates: list[dict[str, Any]] = []
    for script in scripts:
        raw = (script.string or script.text or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        recipe_candidates.extend(extract_recipe_candidates(payload))

    recipe = select_best_recipe(recipe_candidates)
    if not recipe:
        raise RecipeParseError("No JSON-LD recipe found on this page.")

    ingredients = recipe.get("recipeIngredient")
    if not isinstance(ingredients, list):
        ingredients = []
    ingredients = [to_text(item) for item in ingredients if to_text(item)]

    steps = parse_instruction_node(recipe.get("recipeInstructions"))
    parsed_source = urlparse(source_url)

    return {
        "title": to_text(recipe.get("name") or soup.title.string.strip() if soup.title else "Recipe"),
        "description": to_text(recipe.get("description")),
        "source_url": source_url,
        "source_host": parsed_source.netloc,
        "metadata": [
            {"label": "Prep", "value": get_first(recipe.get("prepTime")) or "-"},
            {"label": "Cook", "value": get_first(recipe.get("cookTime")) or "-"},
            {"label": "Total", "value": get_first(recipe.get("totalTime")) or "-"},
            {"label": "Yield", "value": get_first(recipe.get("recipeYield")) or "-"},
            {"label": "Cuisine", "value": get_first(recipe.get("recipeCuisine")) or "-"},
            {"label": "Category", "value": get_first(recipe.get("recipeCategory")) or "-"},
        ],
        "ingredients": ingredients,
        "steps": steps,
        "keywords": to_text(recipe.get("keywords")),
        "nutrition": parse_nutrition(recipe.get("nutrition")),
    }


def parse_recipe_from_url(url: str) -> dict[str, Any]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RecipeParseError(f"Could not fetch URL: {exc}") from exc

    return extract_recipe_from_html(response.text, url)
