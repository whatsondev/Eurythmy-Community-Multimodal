# Eurythmy Community Network

A graph-based knowledge and communication platform for the Community Eurythmy Network, powered by Google Cloud Spanner and Vertex AI.

## Overview

Eurythmy Community Network combines a React frontend with a FastAPI backend to visualise relationships between Practitioners, Specialisms, Venues, and Materials. It features an AI-powered chat interface that allows users to query the graph database using natural language — finding the right movement support, teacher, or therapeutic approach for their needs.

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18 or higher
- **Google Cloud Platform**:
  - Cloud Spanner Instance
  - Vertex AI API enabled (for AI features)
- **Google Cloud Credentials**: A service account key JSON file.

## Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Install dependencies with uv:**
   Make sure you have [uv installed](https://github.com/astral-sh/uv).
   ```bash
   uv sync
   ```

3. **Configuration:**
   - Create a `.env` file in the `backend` directory (see [Environment Variables](#environment-variables)).
   - Place your Google Cloud service account key (e.g., `spanner-key.json`) in the project root or backend directory and reference it in `.env`.

4. **Initialise the Database:**
   Run the script to populate Spanner with the Week 1 seed data.
   ```bash
   uv run python create_property_graph.py
   ```

5. **Run the Server:**
   ```bash
   uv run uvicorn main:app --reload
   ```
   The backend API will be available at `http://localhost:8000`.

## Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configuration:**
   No configuration needed. Defaults to connecting to `http://localhost:8000`.

4. **Run the Development Server:**
   ```bash
   npm run dev
   ```
   The application will be accessible at `http://localhost:5173`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `PROJECT_ID` | GCP Project ID | `your-project-id` |
| `INSTANCE_ID` | Spanner Instance ID | `eurythmy-network` |
| `DATABASE_ID` | Spanner Database ID | `eurythmy-db` |
| `GRAPH_NAME` | Spanner Graph Name | `EurythmyGraph` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key | `../spanner-key.json` |
| `LOCATION` | Vertex AI Location | `us-central1` |
| `USE_MEMORY_BANK` | Enable Memory Bank agent | `True` |

> **Note**: The frontend doesn't require a `.env` file. It connects to the backend at `http://localhost:8000` by default. Can be overridden: `VITE_API_URL=... npm run dev`

## Project Structure

```
eurythmy-community/
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

## Search Test Queries

Use these queries to test that the Smart Router is correctly selecting the right search method.

### 🔀 Hybrid Search

These combine semantic meaning with a specific location or pillar filter.

- **"Therapeutic eurythmy in Birmingham"**
  - *Why*: Combines semantic ("therapeutic") + location filter ("Birmingham") → Ursula Werner at Elysia Therapeutic Centre.
- **"Movement support for grief in the West Midlands"**
  - *Why*: Combines semantic concept + regional context.
- **"Find something for grounding near Stourbridge"**
  - *Why*: Semantic need ("grounding") + location constraint.

### 🧬 Semantic search

These are open or descriptive — no exact keyword match is possible.

- **"Who can help with anxiety?"**
  - *Why*: Abstract therapeutic need → maps to veil work, copper rod eurythmy, Ursula Werner.
- **"Find something for grounding"**
  - *Why*: "Grounding" maps semantically to copper rod eurythmy, Saturn gesture.
- **"Movement support for grief"**
  - *Why*: Grief maps to Moon gesture, veil work, interval of the third.
- **"Find forms for speech and language"**
  - *Why*: Maps to speech eurythmy, Tomie Ando-Boadman, Marie-Reine.

### 🔑 Keyword Search

These are specific and direct — an exact filter match is possible.

- **"Who teaches at Elmfield?"**
  - *Why*: Named venue → Tomie Ando-Boadman.
- **"Venues in Stourbridge"**
  - *Why*: Location filter → Elmfield, Christian Community, Glasshouse Arts Centre.
- **"Therapists in Birmingham"**
  - *Why*: Role category + location.

---

# Verification Guide: Graph Updates

After uploading a session recording or image via the multimodal pipeline, use these steps to verify that the Spanner database and EurythmyGraph have been correctly updated.

## 1. Verify Broadcast Processing (SQL)

Check if the recording was processed and linked to the correct practitioner.

```sql
SELECT
  b.broadcast_id,
  b.title,
  b.processed,
  p.name AS practitioner_name
FROM Broadcasts b
JOIN Practitioners p ON b.practitioner_id = p.practitioner_id
WHERE b.processed = true
ORDER BY b.created_at DESC
LIMIT 1;
```

**Success criteria:**
- `practitioner_name` matches the practitioner in the recording (e.g. `Tomie Ando-Boadman`).
- `processed` is `true`.

## 2. Verify New Specialism or Material Extraction (SQL)

Check if a new Specialism or Material was extracted from the recording.

```sql
SELECT * FROM Specialisms
ORDER BY specialism_id DESC
LIMIT 5;
```

```sql
SELECT * FROM Materials
ORDER BY material_id DESC
LIMIT 5;
```

**Success criteria:** A new row exists matching the form demonstrated in the session (e.g. `Veil Eurythmy`, `Copper Rod`).

## 3. Verify Graph Relationships (GQL)

Use Graph Query Language to confirm the practitioner is now linked to the extracted specialism.

### What did Tomie Ando-Boadman demonstrate recently?

```sql
GRAPH EurythmyGraph
MATCH (p:Practitioner {name: "Tomie Ando-Boadman"})-[h:PractitionerHasSpecialism]->(s:Specialism)
RETURN p.name AS practitioner, h.level, s.name AS specialism
```

### Which venue hosted the most recent session?

```sql
GRAPH EurythmyGraph
MATCH (p:Practitioner)-[a:PractitionerAtVenue]->(v:Venue)
RETURN p.name AS practitioner, v.name AS venue, v.location
```

**Success criteria:** Results match the practitioner and venue visible in the uploaded recording.

## 4. Troubleshooting

If queries return nothing:

1. **Check `Broadcasts` table**: If `processed` is `false` or missing, the upload failed.
2. **Check extraction logs**: The multimodal agent may have failed to identify the practitioner name exactly. Run:
   ```sql
   SELECT * FROM Broadcasts ORDER BY created_at DESC LIMIT 1;
   ```
   If `practitioner_id` is null, the name matching step failed — check the multimedia_agent extraction prompt.
3. **Check embeddings**: If  returns no results, confirm specialism embeddings were generated:
   ```sql
   SELECT name, specialism_embedding IS NOT NULL AS has_embedding FROM Specialisms;
   ```

---

## Privacy and Data

Community Eurythmy is an unincorporated community group. Please observe the following:

- Obtain consent from every practitioner named in the graph before deploying.
- Community group members (May, Janet, Haruko, Chris, Shelagh, Ken) are stored by first name only.
- Do not store medical diagnoses or clinical records against named individuals.
- Memory Bank sessions have a 90-day TTL — do not extend without review.
- GDPR applies. Data controller: **Setsu Adachi** (WhatsOn Agency / Metro Pages Ltd).
