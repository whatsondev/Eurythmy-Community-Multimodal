# Survivor Network

A graph-based analytics and communication platform for survivor communities, powered by Google Cloud Spanner and Vertex AI.

## Overview

Survivor Network combines a React frontend with a FastAPI backend to provide visualize relationships between survivors, skills, and resources. It features an AI-powered chat interface that allows users to query the graph database using natural language.

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Google Cloud Platform**:
  - Cloud Spanner Instance
  - Vertex AI API enabled (for AI features)
- **Google Cloud Credentials**: A service account key JSON file.

## Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Install dependencies with uv:**
    Make sure you have [uv installed](https://github.com/astral-sh/uv).
    ```bash
    uv sync
    ```

3.  **Configuration:**
    - Create a `.env` file in the `backend` directory (see [Environment Variables](#environment-variables)).
    - Place your Google Cloud service account key (e.g., `spanner-key.json`) in the project root or backend directory and reference it in `.env`.

4.  **Initialize the Database:**
    Run the script to populate Spanner with initial sample data.
    ```bash
    uv run python create_property_graph.py
    ```

5.  **Run the Server:**
    ```bash
    uv run uvicorn main:app --reload
    ```
    The backend API will be available at `http://localhost:8000`.

## Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Configuration:**
    - No configuration needed! Defaults to connecting to `http://localhost:8000`.

4.  **Run the Development Server:**
    ```bash
    npm run dev
    ```
    The application will be accessible at `http://localhost:5173`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `PROJECT_ID` | GCP Project ID | `your-project-id` |
| `INSTANCE_ID` | Spanner Instance ID | `survivor-instance` |
| `DATABASE_ID` | Spanner Database ID | `survivor-db` |
| `GRAPH_NAME` | Spanner Graph Name | `SurvivorGraph` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | `../spanner-key.json` |
| `LOCATION` | Vertex AI Location | `us-central1` |
| `USE_MEMORY_BANK` | Enable Memory Bank agent | `True` |

> **Note**: The frontend doesn't require a `.env` file. It connects to the backend at `http://localhost:8000` by default. Can be overridden: `VITE_API_URL=... npm run dev`

## Project Structure

```
eurythmy -community/
├── backend/            # FastAPI Backend
│   ├── agent/          # AI Agent logic
│   ├── api/            # API Routes
│   ├── models/         # Pydantic Models
│   ├── services/       # Spanner & Graph Services
│   └── main.py         # Application Entrypoint
├── frontend/           # React Frontend
│   ├── src/
│   │   ├── components/ # React Components (Chat, Graph, etc.)
│   │   ├── stores/     # State Management (Zustand)
│   │   └── types/      # TypeScript Definitions
│   └── vite.config.ts  # Vite Configuration
└── spanner-key.json    # GCP Credentials (Do not commit!)
```

## Hybrid Search Test Queries

Use these queries to test if the "Smart Router" is correctly choosing the best search method.

### 🔀 Hybrid Search (The "Smart" Queries)

These should trigger the Hybrid method because they combine specific constraints with natural language.

- **"Therapeutic eurythmy in Birmingham"**
  - *Why*: Combines semantic ("therapeutic") + location filter ("Birmingham") → Ursula Werner at Elysia Therapeutic Centre.
- **"Movement support for grief in the West Midlands"**
  - *Why*: Combines semantic concept + regional context.
- **"Find something for grounding near Stourbridge"**
  - *Why*: Semantic need ("grounding") + location constraint.

### 🧬 RAG / Semantic Search (Conceptual)

These should trigger the RAG (Semantic) method because they are vague or ask for similarity.

- **"Who can help with anxiety?"**
  - *Why*: Abstract therapeutic need → maps to veil work, copper rod eurythmy, Ursula Werner.
- **"Find something for grounding"**
  - *Why*: "Grounding" maps semantically to copper rod eurythmy, Saturn gesture.
- **"Movement support for grief"**
  - *Why*: Grief maps to Moon gesture, veil work, interval of the third.
- **"Find forms for speech and language"**
  - *Why*: Maps to speech eurythmy, Tomie Ando-Boadman, Marie-Reine.

### 🔤 Keyword Search (Exact Matches)

These should trigger the Keyword method because they are specific and direct.

- **"Who teaches at Elmfield?"**
  - *Why*: Named venue → Tomie Ando-Boadman.
- **"Venues in Stourbridge"**
  - *Why*: Location filter → Elmfield, Christian Community, Glasshouse Arts Centre.
- **"Therapists in Birmingham"**
  - *Why*: Role category + location.
# Verification Guide: Graph Updates

After uploading the "Field Report" image, use these steps to verify that the Spanner database and Graph have been correctly updated.

## 1. Verify Broadcast Processing (SQL)
Check if the image was processed and linked to **David Chen**.

```sql
SELECT 
  b.broadcast_id, 
  b.title, 
  b.processed, 
  s.name as survivor_name
FROM Broadcasts b
JOIN Survivors s ON b.survivor_id = s.survivor_id
WHERE b.processed = true
ORDER BY b.created_at DESC
LIMIT 1;
```
**Success Criteria:**
- `survivor_name` should be **David Chen**.
- `title` should be related to the field report (or "Upload: image").
- `processed` must be `true`.

## 2. Verify New Resource Creation (SQL)
Check if the **"Energy Crystal"** (or similar extracted name) was added.

```sql
SELECT * FROM Resources 
WHERE name LIKE '%Crystal%' 
OR name LIKE '%Energy%'
ORDER BY resource_id DESC;
```
**Success Criteria:**
- A new row exists with `type` likely inferred (e.g., 'power' or 'tool').

## 3. Verify Graph Relationships (GQL)
Use **Graph Query Language (GQL)** to confirm David Chen is now linked to the new resource and biome.

### Query: What did David Chen find recently?
```sql
GRAPH SurvivorGraph
MATCH (s:Survivor {name: "David Chen"})-[f:FOUND]->(r:Resource)
RETURN s.name AS survivor, f.found_at, r.name AS resource, r.type
```
**Success Criteria:**
- Should return a row linking "David Chen" to "Energy Crystal".

### Query: Where is David Chen now?
```sql
GRAPH SurvivorGraph
MATCH (s:Survivor {name: "David Chen"})-[i:IN_BIOME]->(b:Biome)
RETURN s.name AS survivor, b.name AS biome
```
**Success Criteria:**
- Should return "David Chen" in "Bioluminescent" (or similar extracted biome name).

## 4. Troubleshooting
If the queries return nothing:
1.  **Check `Broadcasts` table**: If `processed` is false or missing, the upload failed.
2.  **Check extraction logs**: The agent might have failed to identify "David Chen" exactly.
    - Run: `SELECT * FROM Broadcasts ORDER BY created_at DESC LIMIT 1` to get the ID.
    - If `survivor_id` is null, the name matching didn't work.
