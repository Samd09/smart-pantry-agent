# 🌱 Smart Pantry & Zero-Waste Chef

An intelligent AI culinary assistant built with Google's **Agent Development Kit (ADK)** and deployed on **Google Cloud Agent Engine**.

![Smart Pantry & Zero-Waste Chef Demo](./demo.gif)

---

## 🚀 Key Features & Capabilities

Based on the implemented codebase in `app/`, the agent provides the following core capabilities:

- **🥑 Pantry & Zero-Waste Recipe Management**: Tracks pantry inventory items, recommends zero-waste recipes using available expiring ingredients, and generates missing ingredient shopping lists.
- **🛡️ Firestore Long-Term Allergy Memory**: Persists user allergies and dietary restrictions in **Google Cloud Firestore** to enforce food safety rules across all recipe recommendations.
- **🎨 Native A2UI (Agent-to-User Interface) Support**: Uses `a2ui-agent-sdk` (v0.8 Basic Catalog) to render dynamic, rich UI components (Cards, Columns, Rows, Texts, Dividers, Images, and Videos) directly inside compatible client UIs.
- **📸 Food Photography Generation**: Uses Vertex AI (`gemini-3.1-flash-lite-image` in the `global` region) to generate food photography images, saving them as ADK artifacts and uploading them directly to **Google Cloud Storage**.
- **🎥 Cooking Demonstration Video Generation**: Uses Google's Omni model (`gemini-omni-flash-preview` via the Vertex AI Interactions API in the `global` region) to create short cooking videos, saving them as ADK artifacts and hosting them on **Google Cloud Storage**.
- **🔍 Web Recipe Search**: Retrieves online recipe instructions and external culinary content using the Google Web Search API.
- **🛒 Location-Aware Grocery Store Search**: Uses Google Maps Geocoding and Places Nearby Search APIs to locate nearby grocery stores and markets.

---

## 🛠️ Google Cloud Services & Integrations

The application is integrated with the following Google Cloud services:

- **Google Cloud Agent Engine (Vertex AI Reasoning Engine)**: Managed runtime hosting the deployed ADK agent (`gemini-2.5-flash`).
- **Google Cloud Firestore**: NoSQL document database storing persistent user allergy records (`user_allergies` collection).
- **Google Cloud Storage (GCS)**: Object storage bucket for generated recipe images (`generated_images/`) and cooking videos (`generated_videos/`).
- **Vertex AI Gemini Models**:
  - `gemini-2.5-flash`: Primary reasoning engine and tool orchestrator.
  - `gemini-3.1-flash-lite-image`: Generates food photography.
  - `gemini-omni-flash-preview`: Generates short cooking video demonstrations.
- **Google Maps Platform**: Geocoding API & Places Nearby Search API for location services.

---

## 💻 Local Development & Setup

### Prerequisites

- Python 3.11+
- `uv` package manager installed
- Google Cloud CLI (`gcloud`) authenticated to your GCP project

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment Variables

Create or update `.env` in the project root:

```bash
GOOGLE_MAPS_API_KEY="YOUR_GOOGLE_MAPS_API_KEY"
```

### 3. Run Agent Playground Locally

Start the local ADK Agent Playground to test tools and memory interactively:

```bash
agents-cli playground --reload_agents
```

### 4. Run Frontend Proxy & Web Interface Locally

To start the FastAPI proxy and web frontend locally:

```bash
cd frontend
pip install -r requirements.txt

# Set target Agent Engine resource and directory
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_ID>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"

python main.py
```

---

## ☁️ Deployment

### Deploying the Agent to Agent Engine

Deploy or update the agent runtime on Google Cloud Agent Engine:

```bash
agents-cli deploy --no-confirm-project --update-env-vars "GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY"
```

### Deploying the Frontend to Cloud Run

Deploy the FastAPI proxy frontend to Google Cloud Run:

```bash
cd frontend
gcloud run deploy smart-pantry-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_ENGINE_RESOURCE_NAME=$AGENT_ENGINE_RESOURCE_NAME,AGENT_DIRECTORY=$AGENT_DIRECTORY"
```
