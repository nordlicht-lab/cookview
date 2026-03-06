import hashlib

import streamlit as st

from parser import RecipeParseError, parse_recipe_from_url

st.set_page_config(page_title="CookView Streamlit", page_icon="🍳", layout="wide")

st.title("CookView")
st.caption("Paste a recipe URL and extract JSON-LD into a compact cooking view.")


def recipe_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def reset_state(key: str, ingredients: int, steps: int):
    st.session_state[f"{key}_ingredients_done"] = [False] * ingredients
    st.session_state[f"{key}_steps_done"] = [False] * steps


url = st.text_input("Recipe URL", placeholder="https://example.com/recipe")
parse_clicked = st.button("Extract", type="primary")

if parse_clicked:
    if not url.strip():
        st.error("Please enter a URL.")
    else:
        try:
            with st.spinner("Extracting recipe..."):
                recipe = parse_recipe_from_url(url.strip())
            key = recipe_key(url.strip())
            st.session_state["recipe"] = recipe
            st.session_state["recipe_key"] = key
            reset_state(key, len(recipe.get("ingredients", [])), len(recipe.get("steps", [])))
        except RecipeParseError as exc:
            st.error(str(exc))

recipe = st.session_state.get("recipe")
key = st.session_state.get("recipe_key")

if recipe and key:
    st.subheader(recipe.get("title") or "Recipe")
    if recipe.get("description"):
        st.write(recipe["description"])
    st.caption(f"Source: {recipe.get('source_host', '-')}")

    meta = [m for m in recipe.get("metadata", []) if m.get("value") and m["value"] != "-"]
    if meta:
        st.write(" | ".join([f"{m['label']}: {m['value']}" for m in meta]))

    left, right = st.columns([1, 2], gap="large")

    with left:
        st.markdown("### Ingredients")
        ing_done_key = f"{key}_ingredients_done"
        ing_done = st.session_state.get(ing_done_key, [False] * len(recipe.get("ingredients", [])))
        for i, ingredient in enumerate(recipe.get("ingredients", [])):
            checked = st.checkbox(
                ingredient,
                value=ing_done[i] if i < len(ing_done) else False,
                key=f"{key}_ingredient_{i}",
            )
            if i < len(ing_done):
                ing_done[i] = checked
        st.session_state[ing_done_key] = ing_done

    with right:
        st.markdown("### Steps")
        step_done_key = f"{key}_steps_done"
        step_done = st.session_state.get(step_done_key, [False] * len(recipe.get("steps", [])))
        for i, step in enumerate(recipe.get("steps", [])):
            checked = st.checkbox(
                f"{i + 1}. {step}",
                value=step_done[i] if i < len(step_done) else False,
                key=f"{key}_step_{i}",
            )
            if i < len(step_done):
                step_done[i] = checked
        st.session_state[step_done_key] = step_done

    with st.expander("Additional Info", expanded=False):
        if recipe.get("nutrition"):
            st.markdown("**Nutrition**")
            for item in recipe["nutrition"]:
                st.write(f"- {item['label']}: {item['value']}")
        st.write(f"Keywords: {recipe.get('keywords') or '-'}")
