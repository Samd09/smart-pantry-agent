# My Agent: Smart Pantry & Zero-Waste Chef

**One-liner**: A conversational agent that helps home cooks minimize food waste by tracking pantry inventory, remembering dietary preferences, and generating customized recipes from ingredients nearing expiration.

## Tool Coverage

- **Memory**: Remembers user's dietary restrictions (e.g., gluten-free, vegan, nut allergy), household size, available kitchen appliances (e.g., air fryer, instant pot), and disliked ingredients.
- **Tools**:
  - `get_pantry_inventory`: Retrieve current items in fridge/pantry along with expiration status.
  - `add_pantry_item`: Add new items with item name, quantity, and expiration date.
  - `search_recipes_by_pantry`: Match expiring pantry items to recipe ideas tailored to dietary rules.
  - `generate_shopping_list`: Create a missing-ingredient shopping list for chosen recipes.
- **Catalog / UI**:
  - Pantry inventory table with color-coded expiration urgency.
  - Recipe recommendation cards with prep time, difficulty, and ingredient match percentages.
- **Image Gen**: Generates a high-quality preview image of the final plated dish with any custom ingredient substitutions.
- **Sandbox**: Calculates recipe scaling, serving ratio adjustments, and nutritional macro breakdown.

## Workshop Recommendations & Stretch Goals

- **Recommended**: Memory Bank (dietary prefs & history), Firestore (pantry inventory & recipe catalog), A2UI (pantry table & recipe cards), Image Generation (dish previews).
- **Stretch Goals**: Code Sandbox for metric unit conversion & ingredient ratio scaling, live Maps integration for nearby store stock lookup.
