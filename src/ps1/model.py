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


OBS_DTYPES = {"route_id": "category", "from_stop": "category", "to_stop": "category",
              "vehicle_id": "category", "source": "category"}


def read_obs(path) -> pd.DataFrame:
    """Stretch observations with compact types: a month is tens of millions of rows."""
    obs = pd.read_csv(path, dtype=OBS_DTYPES)
    # GTFS ids are plain integers, so pandas reads the categories as numbers: make them text again
    for c in ("route_id", "from_stop", "to_stop", "vehicle_id"):
        if c in obs and obs[c].cat.categories.dtype != object and str(obs[c].cat.categories.dtype) != "str":
            obs[c] = obs[c].cat.rename_categories(obs[c].cat.categories.astype(str))
    return obs


def add_time_fields(obs: pd.DataFrame) -> pd.DataFrame:
    """IST hour, day and day type, computed with integers (IST has no daylight saving)."""
    local = obs.t0.to_numpy(float) + 19800
    day_n = (local // 86400).astype(np.int64)
    uniq, inv = np.unique(day_n, return_inverse=True)
    names = [(datetime(1970, 1, 1) + timedelta(days=int(d))).strftime("%Y-%m-%d") for d in uniq]
    weekend = ((day_n + 3) % 7) >= 5  # 1 Jan 1970 was a Thursday
    return obs.assign(hour=((local % 86400) // 3600).astype(np.int64),
                      day=pd.Categorical.from_codes(inv, names),
                      daytype=pd.Categorical.from_codes(weekend.astype(np.int8), ["weekday", "weekend"]))


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
    table = np.full((2, 24), R["*:*"])
    for di, d in enumerate(("weekday", "weekend")):
        for h in range(24):
            table[di, h] = R.get(f"{d}:{h}", R.get(f"*:{h}", R["*:*"]))
    hours = obs.hour.to_numpy(np.int64)
    r_obs = table[(obs.daytype.astype(str).to_numpy() == "weekend").astype(int), hours]
    e1 = pd.Series(np.clip(np.log(obs.travel_s.to_numpy() / (base.to_numpy() * r_obs)), -CLIP, CLIP))
    # one integer id per stretch (stop pair), and its "from>to" name
    pk = obs.groupby(["from_stop", "to_stop"], observed=True, sort=False).ngroup().to_numpy()
    first = pd.DataFrame({"pk": pk, "f": obs.from_stop.astype(str).to_numpy(),
                          "t": obs.to_stop.astype(str).to_numpy()}).drop_duplicates("pk").set_index("pk")
    name = (first.f + ">" + first.t).sort_index()
    g1 = e1.groupby(pk)
    n1 = g1.size()
    pair_log = g1.sum() / (n1 + W_PAIR)
    pair = {name[k]: [round(math.exp(v), 4), int(n)] for k, v, n in zip(pair_log.index, pair_log, n1)}
    e2 = e1 - pair_log.reindex(pk).to_numpy()
    g2 = e2.groupby(pk * 24 + hours)
    n2 = g2.size()
    ph_log = g2.sum() / (n2 + W_PAIR_HOUR)
    pair_hour = {f"{name[k // 24]}@{k % 24}": [round(math.exp(v), 4), int(n)]
                 for k, v, n in zip(ph_log.index, ph_log, n2) if abs(v) > 0.01}
    return TravelModel(a, b, R, n_hour, pair, pair_hour, int(len(obs)), sorted(obs.day.unique().tolist()))


if __name__ == "__main__":
    from .matcher import OBS_FILE
    obs = read_obs(OBS_FILE)
    m = fit(obs)
    MODEL_FILE.write_text(m.to_json())
    print(f"fit on {m.n_obs} observations over {len(m.days)} day(s); prior {m.a:.0f}s + {m.b * 1000:.0f}s/km")
    print("hour factors:", {k: round(v, 2) for k, v in sorted(m.R.items()) if k.startswith("*:")})
    print(f"{len(m.pair)} stretches with their own factor")
