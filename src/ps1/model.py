"""Travel-time model learned from observed stop-to-stop bus traversals.

Prediction for the stretch between stops (f, t) of length L at hour h on day type d:

    time = prior(L) * R[d, h] * K[f, t] * K[f, t, h]

prior(L)   city-wide time for a stretch of length L (fit a + b*L, all hours)
R[d, h]    city-wide congestion factor for that hour and weekday/weekend
K[f, t]    how much slower or faster this stretch is than the city norm
K[f, t, h] extra effect of this hour on this stretch

K factors are geometric means of observed residuals shrunk toward 1 (no
effect) by n / (n + w). A stretch with few observations stays close to the
city pattern; a well observed one follows its own data. Unseen stretches use
prior(L) * R[d, h] only.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .network import ROOT

IST = timezone(timedelta(hours=5, minutes=30))
MODEL_FILE = ROOT / "data" / "ps1" / "model.json"
W_PAIR, W_PAIR_HOUR = 5.0, 3.0
MIN_CELL = 30           # observations for a city hour cell to stand alone
CLIP = 1.5              # clip log residuals (x4.5) against bad matches


def day_type(dt: datetime) -> str:
    return "weekend" if dt.weekday() >= 5 else "weekday"


def add_time_fields(obs: pd.DataFrame) -> pd.DataFrame:
    t = pd.to_datetime(obs.t0, unit="s", utc=True).dt.tz_convert(IST)
    return obs.assign(hour=t.dt.hour, day=t.dt.strftime("%Y-%m-%d"),
                      daytype=np.where(t.dt.day_of_week >= 5, "weekend", "weekday"))


@dataclass
class TravelModel:
    a: float
    b: float
    R: dict                  # "weekday:8" -> factor, "*:8" -> pooled, "*:*" -> overall
    n_hour: dict
    pair: dict               # "f>t" -> [factor, n]
    pair_hour: dict          # "f>t@h" -> [factor, n]
    n_obs: int
    days: list

    def prior(self, dist_m):
        return self.a + self.b * dist_m

    def hour_factor(self, daytype, hour):
        for key in (f"{daytype}:{hour}", f"*:{hour}"):
            if key in self.R:
                return self.R[key], key
        # no data for this hour yet: borrow from the nearest observed hour
        observed = sorted(int(k.split(":")[1]) for k in self.R if k.startswith("*:") and k != "*:*")
        if observed:
            near = min(observed, key=lambda x: min(abs(x - hour), 24 - abs(x - hour)))
            return self.R[f"*:{near}"], f"nearest:{near}"
        return self.R.get("*:*", 1.0), "*:*"

    def predict(self, f, t, dist_m, hour, daytype):
        """Seconds for one stretch, plus how many observations back it."""
        r, _ = self.hour_factor(daytype, hour)
        k, n = self.pair.get(f"{f}>{t}", (1.0, 0))
        kh, nh = self.pair_hour.get(f"{f}>{t}@{hour}", (1.0, 0))
        return float(self.prior(dist_m) * r * k * kh), n

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def load(cls, path=MODEL_FILE):
        return cls(**json.loads(path.read_text()))


def fit(obs: pd.DataFrame) -> TravelModel:
    obs = add_time_fields(obs) if "hour" not in obs else obs
    obs = obs[(obs.travel_s > 0) & (obs.dist_m > 0)]
    # prior: least squares on distance-bin medians (robust to outliers, keeps dwell as intercept)
    bins = pd.qcut(obs.dist_m, q=min(20, max(2, len(obs) // 50)), duplicates="drop")
    med = obs.groupby(bins, observed=True).agg(d=("dist_m", "median"), t=("travel_s", "median"))
    b, a = np.polyfit(med.d, med.t, 1) if len(med) >= 2 else (obs.travel_s.sum() / obs.dist_m.sum(), 0.0)
    a, b = max(float(a), 0.0), max(float(b), 0.02)
    base = a + b * obs.dist_m
    ratio = obs.travel_s / base

    R, n_hour = {"*:*": float(ratio.median())}, {}
    for h, g in ratio.groupby(obs.hour):
        n_hour[f"*:{h}"] = int(len(g))
        if len(g) >= MIN_CELL:  # thinner hours borrow from the nearest observed hour
            R[f"*:{h}"] = float(g.median())
    for (d, h), g in ratio.groupby([obs.daytype, obs.hour]):
        n_hour[f"{d}:{h}"] = int(len(g))
        if len(g) >= MIN_CELL:
            R[f"{d}:{h}"] = float(g.median())
    r_obs = np.array([R.get(f"{d}:{h}", R.get(f"*:{h}", R["*:*"])) for d, h in zip(obs.daytype, obs.hour)])
    e1 = np.clip(np.log(obs.travel_s / (base * r_obs)), -CLIP, CLIP)
    key = obs.from_stop + ">" + obs.to_stop
    g1 = e1.groupby(key)
    pair_log = g1.sum() / (g1.size() + W_PAIR)
    pair = {k: [round(math.exp(v), 4), int(n)] for k, v, n in zip(pair_log.index, pair_log, g1.size())}
    e2 = e1 - key.map(pair_log)
    g2 = e2.groupby(key + "@" + obs.hour.astype(str))
    ph_log = g2.sum() / (g2.size() + W_PAIR_HOUR)
    pair_hour = {k: [round(math.exp(v), 4), int(n)] for k, v, n in zip(ph_log.index, ph_log, g2.size())
                 if abs(v) > 0.01}
    return TravelModel(a, b, R, n_hour, pair, pair_hour, int(len(obs)), sorted(obs.day.unique().tolist()))


if __name__ == "__main__":
    from .matcher import OBS_FILE
    obs = pd.read_csv(OBS_FILE, dtype={"route_id": str, "from_stop": str, "to_stop": str})
    m = fit(obs)
    MODEL_FILE.write_text(m.to_json())
    print(f"fit on {m.n_obs} observations over {len(m.days)} day(s); prior {m.a:.0f}s + {m.b * 1000:.0f}s/km")
    print("hour factors:", {k: round(v, 2) for k, v in sorted(m.R.items()) if k.startswith("*:")})
    print(f"{len(m.pair)} stretches with their own factor")
