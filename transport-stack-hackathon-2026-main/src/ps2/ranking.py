"""Crowd profiles and time-versus-crowd journey ranking."""
from datetime import timedelta

from .model import tier


def _journey(feed, legs, start, get_crowd, score):
    details = []
    for leg in legs:
        points = leg.trip.times[leg.start:leg.end + 1]
        details.append({
            "route": feed.routes[leg.trip.route],
            "routeId": leg.trip.route,
            "tripId": leg.trip.id,
            "serviceDate": leg.service_date.isoformat(),
            "from": feed.stops[points[0].stop],
            "to": feed.stops[points[-1].stop],
            "departure": leg.departure.isoformat(),
            "arrival": leg.arrival.isoformat(),
            "rideMinutes": (leg.arrival - leg.departure).total_seconds() / 60,
            "crowd": get_crowd(leg),
            "points": [feed.stops[point.stop] for point in points],
        })
    scores = [leg["crowd"]["score"] for leg in details]
    return {
        "legs": details,
        "departure": legs[0].departure.isoformat(),
        "arrival": legs[-1].arrival.isoformat(),
        "minutes": round((legs[-1].arrival - start).total_seconds() / 60, 1),
        "waitMinutes": round((legs[0].departure - start).total_seconds() / 60, 1),
        "transfers": len(details) - 1,
        "crowd": {"level": tier(score) if score is not None else "Unknown",
                  "score": round(score, 2) if score is not None else None,
                  "busiestLeg": tier(max(scores)) if score is not None else None},
    }


def recommend(feed, profiles, origin, destination, start, extra_minutes):
    cache = {}

    def get_crowd(leg):
        key = leg.trip.id, leg.service_date, leg.start, leg.end
        if key not in cache:
            cache[key] = profiles.for_leg(leg, feed.trip_patterns[leg.trip.id])
        return cache[key]

    def combined(legs):
        scores = [get_crowd(leg)["score"] for leg in legs]
        if any(score is None for score in scores):
            return None
        weights = [(leg.arrival - leg.departure).total_seconds() for leg in legs]
        total = sum(weights)
        return sum(score * weight for score, weight in zip(scores, weights)) / total if total else scores[0]

    def journey(legs, label, score):
        item = _journey(feed, legs, start, get_crowd, score)
        item["label"] = label
        if label != "Fastest":
            item["extraMinutes"] = round((legs[-1].arrival - best_legs[-1].arrival).total_seconds() / 60, 1)
        return item

    candidates = feed.journeys(origin, destination, start)
    candidates.sort(key=lambda legs: (legs[-1].arrival, len(legs), legs[0].departure))
    if not candidates:
        return {"options": [], "comfortReason": "No scheduled journey found in the next three hours."}
    best_legs = candidates[0]
    limit = best_legs[-1].arrival + timedelta(minutes=extra_minutes)
    baseline = combined(best_legs)
    fastest = journey(best_legs, "Fastest", baseline)
    comfort_legs, comfort_score = None, baseline
    for legs in candidates[1:]:
        if legs[-1].arrival > limit:
            break
        score = combined(legs)
        if score is not None and (baseline is None or score <= baseline - .10) and (
                comfort_score is None or score < comfort_score - .0001):
            comfort_legs, comfort_score = legs, score
    options = [fastest]
    reason = None
    if comfort_legs:
        label = "Less crowded" if baseline is not None else "Crowd estimate available"
        options.append(journey(comfort_legs, label, comfort_score))
    elif baseline is None:
        reason = "Crowd estimates are unavailable for journeys within this time limit."
    else:
        reason = "No lower crowd estimate within your extra-time limit."
    route_sets = {signature(best_legs)}
    if comfort_legs:
        route_sets.add(signature(comfort_legs))
    for legs in candidates:
        if len(options) >= 5:
            break
        key = signature(legs)
        if key in route_sets:
            continue
        options.append(journey(legs, "Alternative", combined(legs)))
        route_sets.add(key)
    return {"options": options, "comfortReason": reason}


def signature(legs):
    return tuple((leg.trip.route, leg.trip.direction,
                  tuple(point.stop for point in leg.trip.times[leg.start:leg.end + 1])) for leg in legs)
