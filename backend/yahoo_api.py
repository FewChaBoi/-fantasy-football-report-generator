"""Yahoo Fantasy API client for web application."""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime

from auth import YahooTokens


# NFL Game IDs by year
NFL_GAME_IDS = {
    2025: 461, 2024: 449, 2023: 423, 2022: 414, 2021: 406,
    2020: 399, 2019: 390, 2018: 380, 2017: 371, 2016: 359,
    2015: 348, 2014: 331, 2013: 314, 2012: 273, 2011: 257,
    2010: 242, 2009: 222, 2008: 199, 2007: 175, 2006: 153,
}


def get_year_from_game_id(game_id: int) -> Optional[int]:
    """Get year from game ID."""
    for year, gid in NFL_GAME_IDS.items():
        if gid == game_id:
            return year
    return None


class YahooFantasyAPI:
    """Yahoo Fantasy API client."""

    BASE_URL = "https://fantasysports.yahooapis.com/fantasy/v2"

    def __init__(self, tokens: YahooTokens):
        self.tokens = tokens

    def _get_headers(self) -> dict:
        """Get request headers with auth."""
        return {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "Content-Type": "application/json",
        }

    async def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make GET request to Yahoo API."""
        url = f"{self.BASE_URL}/{endpoint}"
        if params is None:
            params = {}
        params["format"] = "json"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_user_leagues(self, year: int) -> List[dict]:
        """Get user's leagues for a specific year. Returns list of {league_key, name}."""
        game_id = NFL_GAME_IDS.get(year)
        if not game_id:
            return []

        try:
            data = await self._get(f"users;use_login=1/games;game_keys={game_id}/leagues")
            leagues = []

            # Parse the nested structure
            users = data.get("fantasy_content", {}).get("users", {})
            user = users.get("0", {}).get("user", [])

            if len(user) > 1:
                games = user[1].get("games", {})
                game = games.get("0", {}).get("game", [])

                if len(game) > 1:
                    leagues_data = game[1].get("leagues", {})
                    for key, val in leagues_data.items():
                        if key != "count" and isinstance(val, dict):
                            league_list = val.get("league", [])
                            if league_list and len(league_list) > 0:
                                league_info = league_list[0]
                                if isinstance(league_info, dict) and "league_key" in league_info:
                                    leagues.append({
                                        "league_key": league_info["league_key"],
                                        "name": league_info.get("name", "Unknown League"),
                                    })

            return leagues
        except Exception as e:
            print(f"[API] Error getting leagues for {year}: {e}", flush=True)
            return []

    async def get_league_settings(self, league_key: str) -> dict:
        """Get league settings."""
        data = await self._get(f"league/{league_key}/settings")
        league_data = data.get("fantasy_content", {}).get("league", [])

        result = {}
        # First element is league info
        if league_data and isinstance(league_data[0], list):
            for item in league_data[0]:
                if isinstance(item, dict):
                    result.update(item)
        elif league_data and isinstance(league_data[0], dict):
            result.update(league_data[0])

        return result

    async def get_league_teams(self, league_key: str) -> dict:
        """Get teams in a league."""
        data = await self._get(f"league/{league_key}/teams")

        teams = {}
        league_data = data.get("fantasy_content", {}).get("league", [])

        if len(league_data) > 1:
            teams_data = league_data[1].get("teams", {})
            for key, val in teams_data.items():
                if key != "count" and isinstance(val, dict):
                    team = val.get("team", [[]])[0]
                    team_info = {}
                    for item in team:
                        if isinstance(item, dict):
                            if "team_key" in item:
                                team_info["team_key"] = item["team_key"]
                            elif "name" in item:
                                team_info["name"] = item["name"]
                            elif "managers" in item:
                                managers = item["managers"]
                                if managers:
                                    mgr = managers[0].get("manager", {})
                                    team_info["manager"] = mgr.get("nickname", "Unknown")

                    if "team_key" in team_info:
                        teams[team_info["team_key"]] = team_info

        return teams

    async def get_league_standings(self, league_key: str) -> List[dict]:
        """Get league standings."""
        # Use basic standings endpoint - fallback calculation handles missing data
        data = await self._get(f"league/{league_key}/standings")

        standings = []
        league_data = data.get("fantasy_content", {}).get("league", [])
        print(f"[STANDINGS] Fetching standings for {league_key}", flush=True)

        if len(league_data) > 1:
            # Navigate to teams - handle different possible structures
            standings_container = league_data[1].get("standings", {})

            # Debug: print the standings container structure
            print(f"[STANDINGS DEBUG] standings_container type: {type(standings_container)}", flush=True)
            if isinstance(standings_container, dict):
                print(f"[STANDINGS DEBUG] standings_container keys: {list(standings_container.keys())[:5]}", flush=True)
            elif isinstance(standings_container, list) and standings_container:
                print(f"[STANDINGS DEBUG] standings_container[0] type: {type(standings_container[0])}", flush=True)

            # Try to get teams from different possible structures
            teams_data = {}
            if isinstance(standings_container, list) and standings_container:
                teams_data = standings_container[0].get("teams", {})
            elif isinstance(standings_container, dict):
                # Maybe it's standings.0.teams or just standings.teams
                if "0" in standings_container:
                    teams_data = standings_container["0"].get("teams", {})
                elif "teams" in standings_container:
                    teams_data = standings_container["teams"]

            print(f"[STANDINGS DEBUG] teams_data keys: {list(teams_data.keys())[:5] if isinstance(teams_data, dict) else 'not a dict'}", flush=True)

            first_printed = False

            for key, val in teams_data.items():
                if key != "count" and isinstance(val, dict):
                    team = val.get("team", [])
                    team_info = {}

                    # Debug: print raw team structure for first team
                    if not first_printed:
                        print(f"[STANDINGS DEBUG] Raw team structure (first 2 elements): {team[:2] if isinstance(team, list) else team}", flush=True)
                        if isinstance(team, list) and len(team) > 1:
                            print(f"[STANDINGS DEBUG] team[1] content: {team[1]}", flush=True)
                        first_printed = True

                    # Parse team info from team[0]
                    if team and len(team) > 0 and isinstance(team[0], list):
                        for item in team[0]:
                            if isinstance(item, dict):
                                if "team_key" in item:
                                    team_info["team_key"] = item["team_key"]
                                elif "name" in item:
                                    team_info["name"] = item["name"]
                                elif "managers" in item:
                                    managers = item["managers"]
                                    if managers:
                                        mgr = managers[0].get("manager", {})
                                        team_info["manager"] = mgr.get("nickname", "Unknown")
                                # Check if team_standings is directly in the team info items
                                elif "team_standings" in item:
                                    standings_info = item["team_standings"]
                                    self._parse_standings_info(team_info, standings_info)

                    # Parse standings info from team[1] if not found above
                    if "rank" not in team_info and len(team) > 1 and isinstance(team[1], dict):
                        standings_info = team[1].get("team_standings", {})

                        # If team_standings not found, check if the data is directly in team[1]
                        if not standings_info:
                            # Maybe rank/wins are directly in team[1]
                            if "rank" in team[1]:
                                standings_info = team[1]
                            elif "outcome_totals" in team[1]:
                                standings_info = team[1]

                        self._parse_standings_info(team_info, standings_info)

                    print(f"[STANDINGS] Team: {team_info.get('name', 'Unknown')}, Rank: {team_info.get('rank', 0)}, W: {team_info.get('wins', 0)}", flush=True)

                    standings.append(team_info)

        return standings

    def _parse_standings_info(self, team_info: dict, standings_info: dict) -> None:
        """Parse standings info into team_info dict."""
        if not standings_info:
            return

        rank_val = standings_info.get("rank", 0)
        team_info["rank"] = int(rank_val) if rank_val else 0
        team_info["points_for"] = float(standings_info.get("points_for", 0))
        team_info["points_against"] = float(standings_info.get("points_against", 0))

        outcomes = standings_info.get("outcome_totals", {})
        team_info["wins"] = int(outcomes.get("wins", 0))
        team_info["losses"] = int(outcomes.get("losses", 0))
        team_info["ties"] = int(outcomes.get("ties", 0))

    async def get_matchups(self, league_key: str, week: int) -> List[dict]:
        """Get matchups for a specific week."""
        try:
            data = await self._get(f"league/{league_key}/scoreboard;week={week}")

            matchups = []
            league_data = data.get("fantasy_content", {}).get("league", [])

            if len(league_data) > 1:
                scoreboard = league_data[1].get("scoreboard", {})
                matchups_data = scoreboard.get("0", {}).get("matchups", {})

                for key, val in matchups_data.items():
                    if key == "count" or not isinstance(val, dict):
                        continue

                    matchup = val.get("matchup", {})
                    teams_data = matchup.get("0", {}).get("teams", {})

                    t1_data = teams_data.get("0")
                    t2_data = teams_data.get("1")

                    if not t1_data or not t2_data:
                        continue

                    t1 = self._parse_team_matchup(t1_data)
                    t2 = self._parse_team_matchup(t2_data)

                    is_playoff = matchup.get("is_playoffs", "0") == "1"

                    matchups.append({
                        "week": week,
                        "team1": t1,
                        "team2": t2,
                        "is_playoff": is_playoff,
                    })

            return matchups
        except Exception:
            return []

    def _parse_team_matchup(self, team_data: dict) -> dict:
        """Parse team data from matchup."""
        info = {}
        team = team_data.get("team", [])

        if team and len(team) > 0:
            for item in team[0]:
                if isinstance(item, dict):
                    if "team_key" in item:
                        info["team_key"] = item["team_key"]
                    elif "name" in item:
                        info["name"] = item["name"]
                    elif "managers" in item:
                        managers = item["managers"]
                        if managers:
                            mgr = managers[0].get("manager", {})
                            info["manager"] = mgr.get("nickname", "Unknown")

        if len(team) > 1:
            info["points"] = float(team[1].get("team_points", {}).get("total", 0))

        return info

    async def get_transactions(self, league_key: str, tran_type: str, count: int = 100) -> List[dict]:
        """Get transactions of a specific type."""
        try:
            data = await self._get(
                f"league/{league_key}/transactions;types={tran_type};count={count}"
            )

            transactions = []
            league_data = data.get("fantasy_content", {}).get("league", [])

            if len(league_data) > 1:
                trans_data = league_data[1].get("transactions", {})

                for key, val in trans_data.items():
                    if key == "count" or not isinstance(val, dict):
                        continue

                    transaction = val.get("transaction", [])
                    if not transaction:
                        continue

                    txn_info = {}
                    for item in transaction[0]:
                        if isinstance(item, dict):
                            txn_info.update(item)

                    if len(transaction) > 1:
                        txn_info["players"] = transaction[1].get("players", {})

                    transactions.append(txn_info)

            return transactions
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []


async def discover_league_history(api: YahooFantasyAPI, initial_league_key: str) -> tuple:
    """
    Discover all historical seasons for a league by tracing the 'renew' chain.

    Returns:
        tuple: (list of (league_key, year) tuples, league_name)
    """
    # Parse initial league key
    parts = initial_league_key.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid league key format: {initial_league_key}")

    initial_game_id = int(parts[0])
    initial_year = get_year_from_game_id(initial_game_id)

    # Get league name and settings
    try:
        settings = await api.get_league_settings(initial_league_key)
        league_name = settings.get("name", "Unknown League")
        print(f"[HISTORY] Starting league: {league_name} ({initial_league_key})", flush=True)
    except Exception as e:
        print(f"[HISTORY] Error getting initial settings: {e}", flush=True)
        league_name = "Fantasy Football League"
        settings = {}

    found_leagues = [(initial_league_key, initial_year)]

    # Trace backwards using 'renew' field
    # Format: "449_516875" means game 449, league 516875
    current_key = initial_league_key
    current_settings = settings

    while True:
        renew = current_settings.get("renew", "")
        if not renew or "_" not in renew:
            print(f"[HISTORY] No more renew chain: '{renew}'", flush=True)
            break

        try:
            game_id_str, league_id = renew.split("_")
            game_id = int(game_id_str)
            prev_league_key = f"{game_id}.l.{league_id}"
            prev_year = get_year_from_game_id(game_id)

            if prev_year is None:
                print(f"[HISTORY] Unknown game ID: {game_id}", flush=True)
                break

            print(f"[HISTORY] Found previous season: {prev_year} -> {prev_league_key}", flush=True)

            # Verify we can access this league
            prev_settings = await api.get_league_settings(prev_league_key)
            prev_name = prev_settings.get("name", "")

            found_leagues.append((prev_league_key, prev_year))
            current_key = prev_league_key
            current_settings = prev_settings

        except Exception as e:
            print(f"[HISTORY] Error tracing renew chain: {e}", flush=True)
            break

    # Sort by year (oldest first)
    found_leagues.sort(key=lambda x: x[1])

    print(f"[HISTORY] Found {len(found_leagues)} seasons: {[y for _, y in found_leagues]}", flush=True)

    return found_leagues, league_name
