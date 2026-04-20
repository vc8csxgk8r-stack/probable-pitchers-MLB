from flask import Flask, render_template, request
import requests
from datetime import date
from functools import lru_cache

app = Flask(__name__)

SEASON = "2026"

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
    # ... (la fonction reste IDENTIQUE à la version précédente que je t'ai donnée)
    # (je ne la recopie pas ici pour gagner de la place, garde exactement celle d'avant)
    pass  # ← remplace par la fonction complète que tu as déjà

def get_matchup_grade(era_str, venue_name, opponent_win_pct=None):
    # ... (identique à avant)
    pass

@app.route("/")
def index():
    selected_date = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    standings = get_standings()
    
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {"sportId": 1, "date": selected_date, "hydrate": "probablePitcher,venue"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except:
        data = {"dates": []}
    
    games = []
    if data.get("dates") and len(data["dates"]) > 0:
        for game in data["dates"][0]["games"]:
            away = game["teams"]["away"]
            home = game["teams"]["home"]
            venue_name = game.get("venue", {}).get("name", "—")
            
            # Away pitcher
            away_p = away.get("probablePitcher", {})
            away_id = away_p.get("id")
            away_name = away_p.get("fullName", "TBD")
            away_stats = get_pitcher_stats(away_id)
            away_opp_winpct = standings.get(home["team"]["id"])
            away_grade, away_note = get_matchup_grade(away_stats["era"], venue_name, away_opp_winpct)
            
            # Home pitcher
            home_p = home.get("probablePitcher", {})
            home_id = home_p.get("id")
            home_name = home_p.get("fullName", "TBD")
            home_stats = get_pitcher_stats(home_id)
            home_opp_winpct = standings.get(away["team"]["id"])
            home_grade, home_note = get_matchup_grade(home_stats["era"], venue_name, home_opp_winpct)
            
            games.append({
                "time": game["gameDate"][11:16] + " UTC",
                "away_team": away["team"]["name"],
                "home_team": home["team"]["name"],
                "away_pitcher": {"id": away_id, "name": away_name, "stats": away_stats, "grade": away_grade, "note": away_note},
                "home_pitcher": {"id": home_id, "name": home_name, "stats": home_stats, "grade": home_grade, "note": home_note},
                "venue": venue_name
            })
    
    return render_template("index.html", games=games, selected_date=selected_date)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
