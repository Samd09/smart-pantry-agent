import datetime
from google.cloud import firestore

# HARDCODED Project ID as required for Agent Platform deployment safety
FIRESTORE_PROJECT = "qwiklabs-gcp-01-8bbffcca2465"
db = firestore.Client(project=FIRESTORE_PROJECT)

pantry_items = [
    {
        "name": "Greek Yogurt",
        "category": "Dairy",
        "quantity": 500,
        "unit": "g",
        "days_until_expiration": 2,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "name": "Spinach",
        "category": "Produce",
        "quantity": 200,
        "unit": "g",
        "days_until_expiration": 1,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "name": "Eggs",
        "category": "Dairy",
        "quantity": 6,
        "unit": "pcs",
        "days_until_expiration": 5,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "name": "Avocado",
        "category": "Produce",
        "quantity": 2,
        "unit": "pcs",
        "days_until_expiration": 3,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "name": "Chicken Breast",
        "category": "Meat",
        "quantity": 400,
        "unit": "g",
        "days_until_expiration": 2,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
]

recipes = [
    {
        "name": "Spinach & Feta Egg Scramble",
        "ingredients": ["Spinach", "Eggs"],
        "prep_time_mins": 10,
        "cuisine": "Mediterranean",
        "dietary": ["Vegetarian", "Gluten-Free"],
        "instructions": "Whisk eggs, sauté spinach, mix in pan until cooked.",
    },
    {
        "name": "Avocado Chicken Bowl",
        "ingredients": ["Chicken Breast", "Avocado", "Spinach"],
        "prep_time_mins": 20,
        "cuisine": "American",
        "dietary": ["Gluten-Free", "High-Protein"],
        "instructions": "Grill chicken breast, slice avocado, serve over spinach bed.",
    },
    {
        "name": "Greek Yogurt Berry Parfait",
        "ingredients": ["Greek Yogurt"],
        "prep_time_mins": 5,
        "cuisine": "Breakfast",
        "dietary": ["Vegetarian"],
        "instructions": "Layer yogurt with honey or fresh fruit.",
    },
]


def seed():
    print(f"Seeding Firestore in project: {FIRESTORE_PROJECT}...")
    pantry_ref = db.collection("pantry_items")
    for item in pantry_items:
        doc_ref = pantry_ref.document(item["name"].lower().replace(" ", "_"))
        doc_ref.set(item)
        print(f"  ✓ Added pantry item: {item['name']}")

    recipes_ref = db.collection("recipes")
    for recipe in recipes:
        doc_ref = recipes_ref.document(recipe["name"].lower().replace(" ", "_"))
        doc_ref.set(recipe)
        print(f"  ✓ Added recipe: {recipe['name']}")

    print("Firestore seeding complete!")


if __name__ == "__main__":
    seed()
