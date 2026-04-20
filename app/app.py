from flask import Flask, render_template, request
import requests
from datetime import date
from functools import lru_cache

app = Flask(__name__)

SEASON = "2026"

# ==================== PARK FACTORS ====================
PARK_FACTORS = {
    "Coors Field": -1, "Great American Ball Park": -0.5, "Yankee Stadium": -0.5,
    "Fenway Park": -0.5, "Oracle Park": 1, "Dodger Stadium": 1, "T-Mobile Park": 1,
    "PETCO Park": 1, "Nationals Park": 0.5, "Progressive Field": 0.5,
    "Angel Stadium": 0.5, "Busch Stadium": 0.5,
}

@lru_cache(maxsize=1)
def get_standings():
    url = f"https://statsapi.mlb.com/api/v1/standings?season={SEASON}&leagueId=103,104"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        standings = {}
        for record in data.get("records", []):
            for team in record.get("teamRecords", []):
                standings[team["team"]["id"]] = float(team["leagueRecord"]["pct"])
        return standings
    except:
        return {}

def get_pitcher_stats(pitcher_id):
    """Version complète et robuste"""
    if not pitcher_id:
        return {"era": "—", "record": "—", "whip": "—", "k9": "—"}

    # Essai saison 2026
    url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}"
    params = {"hydrate": f"stats(group=[pitching],type=[season],season={SEASON})"}
    
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        people = data.get("people", [])
        if people:
            stats_list = people[0].get("stats", [])
            for group in stats_list:
                if group.get("group", {}).get("displayName") == "pitching":
                    splits = group.get("splits", [])
                    if splits:
                        stat = splits[0].get("stat", {})
                        ip = float(stat.get("inningsPitched", 0) or 0)
                        so = int(stat.get("strikeOuts", 0) or 0)
                        k9 = round(so / ip * 9, 1) if ip > 0 else 0.0
                        return {
                            "era": stat.get("era", "—"),
                            "record": f"{stat.get('wins',0)}-{stat.get('losses',0)}",
                            "whip": stat.get("whip", "—"),
                            "k9": k9
                        }
    except:
        pass

    # Fallback saison 2025 (début de saison)
    try:
        params["hydrate"] = f"stats(group=[pitching],type=[season],season=2025)"
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        people = data.get("people", [])
        if people:
            stats_list = people[0].get("stats", [])
            for group in stats_list:
                if group.get("group", {}).get("displayName") == "pitching":
                    splits = group.get("splits", [])
                    if splits:
                        stat = splits[0].get("stat", {})
                        ip = float(stat.get("inningsPitched", 0) or 0)
                        so = int(stat.get("strikeOuts", 0) or 0)
                        k9 =
