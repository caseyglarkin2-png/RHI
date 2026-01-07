# Radar Health Index (RHI) Platform — MVP

## Quickstart (local)

### Option A: Docker (recommended)

```bash
docker compose up --build
```

* Frontend: http://localhost:3000
* Backend: http://localhost:8000/api/v1/health
* Backend docs: http://localhost:8000/docs

### Option B: Run services separately

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## What's implemented (MVP)

* **As-of semantics (LOCF)** + month-of-year baseline bucketing
* **Robust z-score** (MAD×1.4826) + monotone and Goldilocks scoring
* **Staleness half-life** drift toward neutral
* **Component aggregation** + driver decomposition (top movers vs yesterday)
* **Dashboard UI:** headline score, radar chart, driver waterfall

## Status + deployment reality check

* The backend should launch locally with `uvicorn main:app --reload --port 8000`.
* The frontend requires a Node/Next build environment (local dev, Vercel, etc.).
* For "live" deployment:
  * Deploy `/backend` as a Docker web service (Render/Fly/Railway/etc).
  * Set CORS env `RHI_FRONTEND_ORIGIN` to your frontend domain.
  * Deploy `/frontend` to Vercel and set `NEXT_PUBLIC_API_BASE_URL` to your backend URL.

This MVP uses seeded mock data so it runs with zero API keys.

## Architecture

### Backend (FastAPI)
- **RHIMathEngine**: Core mathematical engine with:
  - Robust Z-Score normalization (MAD-based, outlier resistant)
  - Staleness decay calculation (exponential half-life)
  - Scoring functions: Goldilocks (stability) and Monotone (directional)
  - Component aggregation with weighted contributions

- **InMemoryTimeSeriesStore**: LOCF (last observation carried forward) semantics with month-of-year bucketing
- **9 Indicators** across 5 components (Trucking, Ocean, Air, Rail, Macro)
- **Frequency-aware**: Daily, weekly, monthly data with appropriate half-lives
- **Driver Decomposition**: Shows top 10 movers (today vs yesterday)

### Frontend (Next.js + React)
- **App Router**: Modern Next.js 14 with app directory
- **Real-time Updates**: Auto-refresh every 60 seconds
- **Components**: 
  - Headline health score gauge with color-coded status
  - Radar chart showing component balance
  - Driver decomposition bar chart
- **Styling**: Tailwind CSS with custom Radix UI components
- **Error Handling**: Graceful fallback with user-friendly error messages

## Project Structure

```
RHI/
├── backend/
│   ├── main.py                  # FastAPI app with complete RHI logic
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Backend container
│   └── .env.example            # Environment template
├── frontend/
│   ├── app/
│   │   ├── components/ui/      # Reusable UI components
│   │   ├── layout.tsx          # Root layout
│   │   ├── globals.css         # Global styles
│   │   └── page.tsx            # Main dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── Dockerfile              # Frontend container
│   └── .env.example            # Environment template
├── docker-compose.yml          # Orchestration
└── README.md
```

## Next Steps for Production

1. **Real Data Integration**: Replace mock store with TimescaleDB + real API sources (EIA, FRED, etc.)
2. **Authentication**: Add JWT-based auth for API endpoints
3. **WebSocket Updates**: Real-time data push instead of polling
4. **Historical Charts**: Add time series visualization
5. **Alerting**: Email/Slack notifications for threshold breaches
6. **Testing**: Unit tests (pytest), integration tests, E2E tests
7. **Monitoring**: DataDog/New Relic for performance tracking
8. **Caching**: Redis for frequently accessed calculations
9. **CI/CD**: GitHub Actions for automated deployments
10. **Documentation**: API docs, architecture diagrams, runbooks
