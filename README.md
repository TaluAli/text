# NAI Studio Web

A FastAPI + React rewrite of the NovelAI helper, featuring aurora glassmorphism UI, live glass controls, and archive browsing.

## Project Layout
- `backend/` — FastAPI app
  - `app/main.py` — API entrypoint
  - `app/services/novelai.py` — NovelAI request logic (ported from original)
  - `app/services/archive.py` — Image saving, metadata, thumbnails
  - `app/models.py` — Pydantic schemas
  - `requirements.txt` — backend deps
- `frontend/` — React + Vite UI
  - `src/App.jsx` — generator, archive viewer, glass controls
  - `src/styles.css` — aurora + glassmorphism styling

## Running Locally
### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Vite dev server defaults to http://localhost:5173 and is allowed via CORS.

## Usage Notes
1. Set your NovelAI token via the **Set Token** button (stored only in backend memory).
2. Adjust prompts/parameters and click **Generate**; results are saved to `backend/data/archives/<project>/` with metadata JSON and thumbnails.
3. Browse archives via the grid; arrow keys or Prev/Next control navigation.
4. Tweak the glassmorphism look in **Glass Settings**; live CSS variables drive the UI and can be copied for reuse.
