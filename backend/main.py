# /backend/main.py

import os
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================================
# 1) Configuration & Indicator Definitions
# ============================================================================

@dataclass
class IndicatorConfig:
    id: str
    name: str
    component: str
    frequency: str  # "daily", "weekly", "monthly"
    type: str  # "monotone_pos", "monotone_neg", "goldilocks"
    half_life_days: float
    weight_within_component: float


INDICATORS = [
    # Trucking (25%)
    IndicatorConfig(
        id="diesel_price",
        name="Diesel Prices",
        component="Trucking",
        frequency="weekly",
        type="monotone_neg",
        half_life_days=10.0,
        weight_within_component=0.5,
    ),
    IndicatorConfig(
        id="truck_tonnage",
        name="Truck Tonnage Index",
        component="Trucking",
        frequency="monthly",
        type="monotone_pos",
        half_life_days=45.0,
        weight_within_component=0.5,
    ),
    # Ocean (35%)
    IndicatorConfig(
        id="ocean_rate",
        name="Ocean Spot Rates",
        component="Ocean",
        frequency="weekly",
        type="goldilocks",
        half_life_days=10.0,
        weight_within_component=0.6,
    ),
    IndicatorConfig(
        id="port_congestion",
        name="Port Congestion (Days)",
        component="Ocean",
        frequency="daily",
        type="monotone_neg",
        half_life_days=3.0,
        weight_within_component=0.4,
    ),
    # Air (20%)
    IndicatorConfig(
        id="jet_fuel",
        name="Jet Fuel Price",
        component="Air",
        frequency="weekly",
        type="monotone_neg",
        half_life_days=10.0,
        weight_within_component=0.5,
    ),
    IndicatorConfig(
        id="cargo_flights",
        name="Weekly Cargo Flights",
        component="Air",
        frequency="weekly",
        type="monotone_pos",
        half_life_days=10.0,
        weight_within_component=0.5,
    ),
    # Rail (15%)
    IndicatorConfig(
        id="rail_carloads",
        name="Rail Carloads",
        component="Rail",
        frequency="weekly",
        type="monotone_pos",
        half_life_days=10.0,
        weight_within_component=1.0,
    ),
    # Macro (5%)
    IndicatorConfig(
        id="pmi",
        name="PMI Index",
        component="Macro",
        frequency="monthly",
        type="monotone_pos",
        half_life_days=45.0,
        weight_within_component=0.7,
    ),
    IndicatorConfig(
        id="tariff_friction",
        name="Tariff Friction Index",
        component="Macro",
        frequency="monthly",
        type="monotone_neg",
        half_life_days=45.0,
        weight_within_component=0.3,
    ),
]

COMPONENT_WEIGHTS = {
    "Trucking": 0.25,
    "Ocean": 0.35,
    "Air": 0.20,
    "Rail": 0.15,
    "Macro": 0.05,
}


# ============================================================================
# 2) Data Models (Pydantic)
# ============================================================================

class IndicatorScore(BaseModel):
    id: str
    name: str
    component: str
    asof_date: str
    raw_value: float
    z_score: float
    raw_score: float
    staleness_factor: float
    health_score: float


class RHILatestResponse(BaseModel):
    timestamp: datetime
    headline_score: float
    components: Dict[str, Dict[str, float]]
    indicators: List[IndicatorScore]
    driver_decomposition: List[Dict[str, object]]


# ============================================================================
# 3) In-Memory Time Series Store (Mock)
# ============================================================================

class InMemoryTimeSeriesStore:
    """
    Stores time series data as {indicator_id: [(date, value), ...]}.
    """

    def __init__(self):
        self._data: Dict[str, List[tuple[date, float]]] = defaultdict(list)
        self._frozen = False

    def put(self, indicator_id: str, d: date, value: float):
        if self._frozen:
            raise RuntimeError("Store is frozen")
        self._data[indicator_id].append((d, value))

    def finalize(self):
        for indicator_id in self._data:
            self._data[indicator_id].sort(key=lambda x: x[0])
        self._frozen = True

    def get_history_for_month_bucket(
        self, indicator_id: str, target_date: date, baseline_years: int
    ) -> List[float]:
        """
        Returns all values from the same month-of-year over the past N years.
        """
        if indicator_id not in self._data:
            return []

        target_month = target_date.month
        start_year = target_date.year - baseline_years
        values = []

        for d, val in self._data[indicator_id]:
            if d.month == target_month and d.year >= start_year and d < target_date:
                values.append(val)

        return values

    def get_latest_value(self, indicator_id: str, asof_date: date) -> Optional[float]:
        """
        LOCF: Last observation carried forward up to asof_date.
        """
        if indicator_id not in self._data:
            return None

        best = None
        for d, val in self._data[indicator_id]:
            if d > asof_date:
                break
            best = (d, val)

        return best[1] if best else None

    def get_latest_date(self, indicator_id: str, asof_date: date) -> Optional[date]:
        """
        Returns the date of the last observation <= asof_date.
        """
        if indicator_id not in self._data:
            return None

        best = None
        for d, val in self._data[indicator_id]:
            if d > asof_date:
                break
            best = d

        return best


# ============================================================================
# 4) RHI Math Engine
# ============================================================================

class RHIMathEngine:
    """
    Core mathematical engine for the Radar Health Index.
    Implements Robust Z-Score normalization, Staleness Decay, and Scoring.
    """

    MAD_SCALE_FACTOR = 1.4826

    def robust_z_score(self, value: float, history: List[float]) -> float:
        """
        Robust Z-Score using Median and Median Absolute Deviation (MAD).
        Formula: z = (x - median) / (1.4826 * MAD)
        """
        if not history:
            return 0.0

        arr = np.array(history)
        median = np.median(arr)
        mad = np.median(np.abs(arr - median))

        if mad < 1e-6:
            mad = 1e-6

        z = (value - median) / (self.MAD_SCALE_FACTOR * mad)
        return float(z)

    def score_goldilocks(self, z_score: float, sigma_target: float = 1.5) -> float:
        """
        Scores 'stability' where both extremes are bad (e.g., Ocean Rates).
        Returns 0-100 score. 100 = Perfect stability (Z=0).
        """
        score = 100.0 * np.exp(-(z_score**2) / (2.0 * sigma_target**2))
        return float(score)

    def score_monotone(self, z_score: float, direction: str) -> float:
        """
        Scores indicators where higher is better (positive) or lower is better (negative).
        Uses a simple linear mapping: z=0 -> 50, z=+2 -> 100 (pos) or 0 (neg).
        """
        # Simple linear: score = 50 + 25*z for positive, 50 - 25*z for negative
        if direction == "positive":
            score = 50.0 + 25.0 * z_score
        else:
            score = 50.0 - 25.0 * z_score

        # Clamp to [0, 100]
        return float(max(0.0, min(100.0, score)))

    def staleness_factor(
        self, last_update: date, target_date: date, half_life_days: float
    ) -> float:
        """
        Calculates the decay factor based on data age.
        Formula: lambda = exp(-ln(2) * delta_t / half_life)
        """
        delta_days = (target_date - last_update).days
        if delta_days < 0:
            delta_days = 0

        decay = np.exp(-np.log(2.0) * delta_days / half_life_days)
        return float(decay)

    def apply_staleness(self, raw_score: float, decay: float) -> float:
        """
        Applies staleness penalty: score drifts toward neutral (50) as data ages.
        """
        final = raw_score * decay + 50.0 * (1.0 - decay)
        return float(final)


# ============================================================================
# 5) RHI Service
# ============================================================================

class RHIService:
    def __init__(self, store: InMemoryTimeSeriesStore, baseline_years: int = 5):
        self.store = store
        self.baseline_years = baseline_years
        self.engine = RHIMathEngine()

    def _indicator_score(
        self, cfg: IndicatorConfig, target_date: date
    ) -> Optional[IndicatorScore]:
        """
        Compute the health score for a single indicator as of target_date.
        """
        value = self.store.get_latest_value(cfg.id, target_date)
        if value is None:
            return None

        asof_date = self.store.get_latest_date(cfg.id, target_date)
        if asof_date is None:
            return None

        # Get month-of-year baseline
        history = self.store.get_history_for_month_bucket(
            cfg.id, target_date, self.baseline_years
        )
        if not history:
            return None

        # Compute robust z-score
        z = self.engine.robust_z_score(value, history)

        # Score based on type
        if cfg.type == "goldilocks":
            raw = self.engine.score_goldilocks(z)
        elif cfg.type == "monotone_pos":
            raw = self.engine.score_monotone(z, "positive")
        else:  # monotone_neg
            raw = self.engine.score_monotone(z, "negative")

        # Apply staleness decay
        decay = self.engine.staleness_factor(asof_date, target_date, cfg.half_life_days)
        final = self.engine.apply_staleness(raw, decay)

        return IndicatorScore(
            id=cfg.id,
            name=cfg.name,
            component=cfg.component,
            asof_date=asof_date.isoformat(),
            raw_value=float(value),
            z_score=round(float(z), 3),
            raw_score=round(float(raw), 2),
            staleness_factor=round(float(decay), 3),
            health_score=round(float(final), 2),
        )

    def compute_day(self, target_date: date) -> Dict[str, object]:
        """
        Computes the RHI for a specific date.
        """
        indicator_scores: List[IndicatorScore] = []
        for cfg in INDICATORS:
            sc = self._indicator_score(cfg, target_date)
            if sc:
                indicator_scores.append(sc)

        # Component aggregation (weighted mean within each component)
        comp_scores: Dict[str, float] = {}
        for comp in COMPONENT_WEIGHTS.keys():
            relevant = [s for s in indicator_scores if s.component == comp]
            if not relevant:
                comp_scores[comp] = 50.0
                continue

            w_sum, s_sum = 0.0, 0.0
            for s in relevant:
                w = next(c.weight_within_component for c in INDICATORS if c.id == s.id)
                w_sum += w
                s_sum += w * s.health_score
            comp_scores[comp] = (s_sum / w_sum) if w_sum else 50.0

        # Headline aggregation
        headline = 0.0
        for comp, w in COMPONENT_WEIGHTS.items():
            headline += w * comp_scores.get(comp, 50.0)

        # Contributions for driver decomposition
        contributions: Dict[str, float] = {}
        for s in indicator_scores:
            cfg = next(c for c in INDICATORS if c.id == s.id)
            contributions[s.id] = (
                COMPONENT_WEIGHTS[cfg.component]
                * cfg.weight_within_component
                * s.health_score
            )

        return {
            "date": target_date,
            "headline": float(headline),
            "components": comp_scores,
            "indicator_scores": indicator_scores,
            "contributions": contributions,
        }

    def latest(self) -> RHILatestResponse:
        """
        Returns the latest RHI snapshot with driver decomposition.
        """
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        today_res = self.compute_day(today)
        y_res = self.compute_day(yesterday)

        # Driver decomposition (today vs yesterday)
        drivers: List[Dict[str, object]] = []
        for cfg in INDICATORS:
            t = today_res["contributions"].get(cfg.id)
            y = y_res["contributions"].get(cfg.id)
            if t is None or y is None:
                continue
            impact = float(t - y)
            if abs(impact) < 1e-6:
                continue
            drivers.append(
                {
                    "id": cfg.id,
                    "name": cfg.name,
                    "impact": round(impact, 3),
                    "category": cfg.component,
                }
            )

        # Sort by absolute impact, descending, and take top 10
        drivers.sort(key=lambda d: abs(float(d["impact"])), reverse=True)
        drivers = drivers[:10]

        # Prepare component payload
        components_payload = {
            k: {"score": round(v, 2), "weight": COMPONENT_WEIGHTS[k]}
            for k, v in today_res["components"].items()
        }

        return RHILatestResponse(
            timestamp=datetime.now(timezone.utc),
            headline_score=round(float(today_res["headline"]), 2),
            components=components_payload,
            indicators=today_res["indicator_scores"],
            driver_decomposition=drivers,
        )

    def history(self, days: int) -> List[Dict[str, object]]:
        """
        Returns historical RHI data for the last N days.
        """
        days = max(1, min(days, 3650))
        end = datetime.now(timezone.utc).date()
        out: List[Dict[str, object]] = []
        for i in range(days):
            d = end - timedelta(days=i)
            res = self.compute_day(d)
            out.append(
                {
                    "date": d.isoformat(),
                    "headline_score": round(float(res["headline"]), 2),
                    "components": {k: round(v, 2) for k, v in res["components"].items()},
                }
            )
        return list(reversed(out))


# ============================================================================
# 6) Mock Data Seeding
# ============================================================================

def _seed_mock_store() -> InMemoryTimeSeriesStore:
    """
    Seeds the in-memory store with 5 years of synthetic data.
    """
    store = InMemoryTimeSeriesStore()
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * 5)

    random.seed(42)

    # Starting levels
    level = {
        "diesel_price": 4.00,
        "truck_tonnage": 120.0,
        "ocean_rate": 1800.0,
        "port_congestion": 4.0,
        "jet_fuel": 2.50,
        "cargo_flights": 1500.0,
        "rail_carloads": 200000.0,
        "pmi": 51.0,
        "tariff_friction": 1.5,
    }

    # Volatility parameters
    vol = {
        "diesel_price": 0.08,
        "truck_tonnage": 0.4,
        "ocean_rate": 25.0,
        "port_congestion": 0.25,
        "jet_fuel": 0.06,
        "cargo_flights": 8.0,
        "rail_carloads": 1500.0,
        "pmi": 0.25,
        "tariff_friction": 0.03,
    }

    cfg_by_id = {c.id: c for c in INDICATORS}

    d = start
    while d <= end:
        for indicator_id, cfg in cfg_by_id.items():
            # Determine if we should emit based on frequency
            do_emit = (
                cfg.frequency == "daily"
                or (cfg.frequency == "weekly" and d.weekday() == 0)
                or (cfg.frequency == "monthly" and d.day == 1)
            )
            if not do_emit:
                continue

            # Light seasonality so month-bucket baselines actually matter
            seasonal = 0.0
            if indicator_id == "cargo_flights":
                seasonal = 20.0 if d.month in (10, 11, 12) else 0.0
            if indicator_id == "truck_tonnage":
                seasonal = -2.0 if d.month == 2 else 0.0

            # Random shock
            shock = 0.0
            if indicator_id in ("ocean_rate", "port_congestion") and random.random() < 0.01:
                shock = random.choice([-1, 1]) * (5.0 * vol[indicator_id])

            # Update level
            level[indicator_id] = max(
                0.0,
                level[indicator_id]
                + random.gauss(0.0, vol[indicator_id])
                + shock
                + seasonal * 0.01,
            )
            store.put(indicator_id, d, level[indicator_id])

        d += timedelta(days=1)

    store.finalize()
    return store


# ============================================================================
# 7) FastAPI Application
# ============================================================================

BASELINE_YEARS = int(os.getenv("RHI_BASELINE_YEARS", "5"))
FRONTEND_ORIGIN = os.getenv("RHI_FRONTEND_ORIGIN", "http://localhost:3000")

store = _seed_mock_store()
service = RHIService(store, baseline_years=BASELINE_YEARS)

app = FastAPI(title="Radar Health Index API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health():
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/v1/rhi/latest", response_model=RHILatestResponse)
async def rhi_latest():
    return service.latest()


@app.get("/api/v1/rhi/history")
async def rhi_history(days: int = Query(default=90, ge=1, le=3650)):
    return {"days": days, "series": service.history(days)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
