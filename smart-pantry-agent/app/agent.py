# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import datetime
import json
import os
import uuid
from typing import Any, Dict, List

import requests
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext, load_memory_tool, preload_memory_tool
from google.cloud import firestore, storage
from google.genai import Client, types

from app.a2ui_utils import a2ui_callback

load_dotenv()

# Hardcoded GCP Project ID & GCS Bucket Name (Literal strings required)
FIRESTORE_PROJECT = "qwiklabs-gcp-01-8bbffcca2465"
GCS_BUCKET_NAME = "smart-pantry-assets-qwiklabs-gcp-01-8bbffcca2465"

db = firestore.Client(project=FIRESTORE_PROJECT)

# Load Agent Engine & Sandbox resource names from deployment_metadata.json if available
metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
agent_engine_resource_name = None
sandbox_resource_name = None

if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            agent_engine_resource_name = meta.get("remote_agent_runtime_id")
            sandbox_resource_name = meta.get("sandbox_resource_name")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=sandbox_resource_name,
    agent_engine_resource_name=agent_engine_resource_name,
)



def get_pantry_inventory() -> List[Dict[str, Any]]:
    """Retrieve all current pantry items from the Firestore database, sorted by days until expiration.

    Returns:
        List of pantry item dictionaries containing item details like name, category, quantity, unit, and expiration status.
    """
    docs = db.collection("pantry_items").stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        items.append(data)
    items.sort(key=lambda x: x.get("days_until_expiration", 999))
    return items


def add_pantry_item(
    name: str,
    category: str,
    quantity: float,
    unit: str,
    days_until_expiration: int,
) -> str:
    """Add a new ingredient/item to the user's pantry inventory in Firestore.

    Args:
        name: Name of the item (e.g. 'Avocado', 'Milk').
        category: Food category (e.g. 'Dairy', 'Produce', 'Meat', 'Pantry').
        quantity: Amount of the item.
        unit: Unit of measurement (e.g. 'items', 'grams', 'liters', 'cups').
        days_until_expiration: Number of days remaining before expiration.

    Returns:
        Confirmation message string.
    """
    item_id = name.lower().replace(" ", "_")
    item_data = {
        "id": item_id,
        "name": name,
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "days_until_expiration": days_until_expiration,
        "date_added": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    }
    db.collection("pantry_items").document(item_id).set(item_data)
    return f"Successfully added {quantity} {unit} of '{name}' to your pantry (expires in {days_until_expiration} days)."


def search_recipes_by_pantry() -> List[Dict[str, Any]]:
    """Search for recipes in Firestore that can be prepared using available pantry ingredients.

    Returns:
        List of matching recipe dictionaries with title, ingredients, instructions, prep time, and difficulty.
    """
    docs = db.collection("recipes").stream()
    return [doc.to_dict() for doc in docs]


def generate_shopping_list(recipe_title: str, required_ingredients: List[str]) -> Dict[str, Any]:
    """Compare required ingredients for a recipe against current Firestore pantry inventory, identify missing ingredients, and create a shopping list.

    Args:
        recipe_title: Name of the recipe being prepared.
        required_ingredients: List of ingredient names needed for the recipe (e.g. ['Spinach', 'Eggs', 'Feta Cheese', 'Olive Oil']).

    Returns:
        Dictionary containing the recipe title, available ingredients from pantry, missing ingredients to buy, and saved shopping list details.
    """
    pantry_items = get_pantry_inventory()
    pantry_names = {item.get("name", "").lower() for item in pantry_items}

    available = []
    missing = []
    for ing in required_ingredients:
        ing_clean = ing.lower().strip()
        if any(ing_clean in p_name or p_name in ing_clean for p_name in pantry_names if p_name):
            available.append(ing)
        else:
            missing.append(ing)

    list_id = f"list_{recipe_title.lower().replace(' ', '_')}"
    shopping_list_data = {
        "id": list_id,
        "recipe_title": recipe_title,
        "missing_ingredients": missing,
        "available_in_pantry": available,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    db.collection("shopping_lists").document(list_id).set(shopping_list_data)

    return {
        "recipe_title": recipe_title,
        "available_in_pantry": available,
        "missing_ingredients_to_buy": missing,
        "status": "Shopping list generated and saved to Firestore",
    }


def fetch_online_recipes(query: str) -> List[Dict[str, Any]]:
    """Search for real recipes online via DummyJSON Recipes API matching an ingredient or dish name.

    Args:
        query: Ingredient or recipe name to search (e.g. 'chicken', 'pasta', 'salad').

    Returns:
        List of matching recipe summaries with title, cuisine, prep time, difficulty, ingredients, and image URL.
    """
    api_key = os.getenv("RECIPE_API_KEY", "")
    url = f"https://dummyjson.com/recipes/search?q={query}"
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        recipes = data.get("recipes") or []
        results = []
        for r in recipes[:3]:
            results.append({
                "title": r.get("name"),
                "cuisine": r.get("cuisine"),
                "difficulty": r.get("difficulty"),
                "prep_time_minutes": r.get("prepTimeMinutes"),
                "ingredients": r.get("ingredients"),
                "image_url": r.get("image"),
            })
        return results
    except Exception as e:
        return [{"error": f"Failed to fetch online recipes: {e}"}]


def geocode_address(address: str) -> Dict[str, Any]:
    """Geocode a street address or location name into geographic latitude/longitude coordinates using Google Maps Geocoding API.

    Args:
        address: Street address or city/location name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing name, formatted address, and location coordinates (latitude, longitude).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY is not set."}
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    try:
        resp = requests.get(url, params={"address": address, "key": api_key}, timeout=10)
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            return {"error": f"Geocoding failed: {data.get('status', 'NO_RESULTS')}"}
        result = data["results"][0]
        loc = result["geometry"]["location"]
        return {
            "name": address,
            "address": result.get("formatted_address"),
            "location": {
                "latitude": loc.get("lat"),
                "longitude": loc.get("lng"),
            },
        }
    except Exception as e:
        return {"error": f"Failed to geocode address: {e}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "supermarket",
    radius: float = 2000.0,
) -> List[Dict[str, Any]]:
    """Find nearby points of interest (e.g. supermarkets, grocery stores) around coordinates using Places API (New).

    Args:
        latitude: Geographic latitude center point.
        longitude: Geographic longitude center point.
        place_type: Type of place to search for (e.g. 'supermarket', 'grocery_store', 'bakery').
        radius: Search radius in meters (default 2000.0).

    Returns:
        List of matching place dictionaries containing name, address, and location (latitude, longitude).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY is not set."}]
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius,
            }
        },
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code != 200:
            return [{"error": f"Places API failed with status {resp.status_code}: {resp.text[:200]}"}]
        data = resp.json()
        places = data.get("places") or []
        results = []
        for p in places[:5]:
            disp = p.get("displayName", {})
            loc = p.get("location", {})
            name_str = disp.get("text") if isinstance(disp, dict) else str(disp)
            results.append({
                "name": name_str,
                "address": p.get("formattedAddress"),
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
            })
        return results
    except Exception as e:
        return [{"error": f"Failed to find nearby places: {e}"}]


async def generate_recipe_image(prompt: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Generate a realistic food/recipe image using gemini-3.1-flash-lite-image model, save it as a Playground artifact, and upload it to public Cloud Storage.

    Args:
        prompt: Description or name of the food item or recipe to generate an image for (e.g. 'Avocado Toast with Poached Egg').
        tool_context: Active ADK tool context used to record artifacts in the Playground.

    Returns:
        Dictionary containing the image public Cloud Storage HTTPS URL, artifact filename, and generation status.
    """
    try:
        genai_client = Client(
            vertexai=True,
            project=FIRESTORE_PROJECT,
            location="global",
        )
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=f"High quality, realistic food photography of {prompt}",
        )

        img_bytes = None
        mime_type = "image/jpeg"
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not img_bytes:
            return {"error": "Failed to generate image bytes from model response."}

        clean_slug = "".join(c if c.isalnum() else "_" for c in prompt.lower())[:30].strip("_")
        ext = "jpg" if "jpeg" in mime_type else "png"
        filename = f"recipe_{clean_slug}_{uuid.uuid4().hex[:6]}.{ext}"

        # 1. Save artifact with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload image bytes directly to GCS bucket (no local disk file created)
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_path = f"generated_images/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(img_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"

        return {
            "status": "success",
            "image_url": public_url,
            "filename": filename,
            "message": f"Generated image saved as artifact '{filename}' and uploaded to GCS at {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate recipe image: {e}"}


async def generate_recipe_video(
    prompt: str, tool_context: ToolContext = None
) -> Dict[str, Any]:
    """Generates a short recipe or food preparation video for an item in the agent's domain using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Args:
        prompt: Description of the recipe, food preparation, or culinary technique to generate a video for.
        tool_context: ADK ToolContext instance for saving artifacts.

    Returns:
        Dictionary containing the video public Cloud Storage HTTPS URL, artifact filename, and generation status.
    """
    try:
        genai_client = Client(
            vertexai=True,
            project=FIRESTORE_PROJECT,
            location="global",
        )
        interaction = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Short cooking video demonstration of {prompt}",
        )

        video_bytes = None
        mime_type = "video/mp4"

        ov = getattr(interaction, "output_video", None)
        if ov and getattr(ov, "data", None):
            mime_type = getattr(ov, "mime_type", None) or "video/mp4"
            raw_data = ov.data
            if isinstance(raw_data, str):
                video_bytes = base64.b64decode(raw_data)
            elif isinstance(raw_data, bytes):
                video_bytes = raw_data

        if not video_bytes:
            return {"error": "Failed to generate video bytes from model interaction response."}

        clean_slug = "".join(c if c.isalnum() else "_" for c in prompt.lower())[:30].strip("_")
        ext = "mp4" if "mp4" in mime_type else "webm"
        filename = f"video_{clean_slug}_{uuid.uuid4().hex[:6]}.{ext}"

        # 1. Save artifact with tool_context.save_artifact so it shows up in Playground's Artifacts panel
        if tool_context:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)

        # 2. Upload video bytes directly to GCS bucket (no local disk file created)
        storage_client = storage.Client(project=FIRESTORE_PROJECT)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_path = f"generated_videos/{filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"

        return {
            "status": "success",
            "video_url": public_url,
            "filename": filename,
            "message": f"Generated video saved as artifact '{filename}' and uploaded to GCS at {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate recipe video: {e}"}


def get_user_allergies() -> List[Dict[str, Any]]:
    """Retrieve all documented user allergies and dietary restrictions from Firestore database.
    Use this tool before recommending recipes or generating shopping lists to ensure user safety.
    """
    try:
        docs = db.collection("user_allergies").stream()
        results = [doc.to_dict() for doc in docs]
        return results
    except Exception as e:
        return [{"error": f"Failed to retrieve user allergies: {e}"}]


def save_user_allergy(allergy_name: str, severity: str = "high", notes: str = "") -> Dict[str, Any]:
    """Save or update a user allergy or dietary restriction in the Firestore database to ensure it is remembered across sessions.

    Args:
        allergy_name: The name of the allergen or restriction (e.g. Peanuts, Gluten, Dairy, Shellfish).
        severity: Allergy severity level ('high', 'medium', 'low').
        notes: Additional details or specific avoidance notes.
    """
    try:
        clean_id = "".join(c if c.isalnum() else "_" for c in allergy_name.lower()).strip("_")
        data = {
            "allergy_name": allergy_name,
            "severity": severity,
            "notes": notes,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        db.collection("user_allergies").document(clean_id).set(data, merge=True)
        return {
            "status": "success",
            "message": f"Saved allergy '{allergy_name}' to user memory profile in Firestore.",
            "data": data,
        }
    except Exception as e:
        return {"error": f"Failed to save user allergy: {e}"}


def remove_user_allergy(allergy_name: str) -> Dict[str, Any]:
    """Remove an allergy or dietary restriction from the user's remembered profile in Firestore."""
    try:
        clean_id = "".join(c if c.isalnum() else "_" for c in allergy_name.lower()).strip("_")
        db.collection("user_allergies").document(clean_id).delete()
        return {"status": "success", "message": f"Removed allergy '{allergy_name}' from memory profile."}
    except Exception as e:
        return {"error": f"Failed to remove allergy: {e}"}


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_prompt = schema_manager.generate_system_prompt(
    role_description="You are Food-Zone by Samarpan, an AI culinary assistant. You help users track pantry ingredients, find recipes, generate shopping lists, fetch online recipes, find nearby grocery stores using Google Maps, generate realistic food images, and strictly remember user allergies and dietary restrictions.",
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

system_instruction = f"""{a2ui_prompt}

ALLERGY MEMORY & SAFETY INSTRUCTIONS:
- ALWAYS check user allergies using `get_user_allergies()` before suggesting recipes, recommending food, or generating shopping lists.
- NEVER recommend or generate recipes containing ingredients the user is allergic to.
- Whenever the user mentions a new allergy, food intolerance, or dietary restriction, immediately save it using `save_user_allergy(allergy_name, severity, notes)` so it persists permanently across sessions.
- Use `load_memory` to search long-term memory for prior user preferences when needed.

Tool mapping & Capabilities:
- When asked about allergies or user dietary restrictions: call `get_user_allergies()`.
- When user specifies an allergy to remember: call `save_user_allergy(allergy_name, severity, notes)`.
- When user removes an allergy: call `remove_user_allergy(allergy_name)`.
- When asked to geocode an address or find coordinates: call `geocode_address(address)`.
- When asked to find nearby places or grocery stores: call `geocode_address(address)` to get coordinates, then call `find_nearby_places(latitude, longitude, place_type='supermarket')`.
- When asked about pantry inventory: call `get_pantry_inventory()`.
- When asked about internal recipes: call `search_recipes_by_pantry()`.
- When asked for online recipes: call `fetch_online_recipes(query)`.
- When asked for a shopping list: call `generate_shopping_list(recipe_title, required_ingredients)`.
- When asked to generate an image or picture of a recipe/food item: call `generate_recipe_image(prompt)`.
- You can write and execute Python code in your secure Agent Engine sandbox for math calculations, unit conversions, or data analysis.

Always summarize tool outputs and confirm allergy compliance in your response."""


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        client_kwargs={
            "vertexai": True,
            "project": "qwiklabs-gcp-01-8bbffcca2465",
            "location": "us-central1",
        },
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=system_instruction,
    after_model_callback=a2ui_callback,
    tools=[
        get_pantry_inventory,
        add_pantry_item,
        search_recipes_by_pantry,
        generate_shopping_list,
        fetch_online_recipes,
        geocode_address,
        find_nearby_places,
        generate_recipe_image,
        generate_recipe_video,
        get_user_allergies,
        save_user_allergy,
        remove_user_allergy,
        load_memory_tool.load_memory_tool,
        preload_memory_tool.preload_memory_tool,
    ],
)


app = App(
    root_agent=root_agent,
    name="app",
)




