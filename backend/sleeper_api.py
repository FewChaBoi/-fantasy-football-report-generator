"""Sleeper Fantasy API client for web application."""

import httpx
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SleeperUser:
    """Sleeper user information."""
    user_id: str
    username: str
    display_name: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SleeperUser":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            display_name=data["display_name"],
        )


class SleeperFantasyAPI:
    """Sleeper Fantasy API client."""

    BASE_URL = "https://api.sleeper.app/v1"

    def __init__(self, user: SleeperUser):
        self.user = user

    async def _get(self, endpoint: str) -> Any:
        """Make GET request to Sleeper API."""
        url = f"{self.BASE_URL}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def get_nfl_state(self) -> dict:
        """Get current NFL state (season, week)."""
        return await self._get("state/nfl")

    async def get_user_leagues(self, season: int) -> List[dict]:
        """Get user's leagues for a specific season. Returns list of {league_id, name}."""
        try:
            leagues_data = await self._get(f"user/{self.user.user_id}/leagues/nfl/{season}")

            if not leagues_data:
                return []

            leagues = []
            for league in leagues_data:
                leagues.append({
                    "league_id": league.get("league_id"),
                    "name": league.get("name", "Unknown League"),
                    "total_rosters": league.get("total_rosters", 0),
                    "status": league.get("status"),
                    "previous_league_id": league.get("previous_league_id"),
                })

            return leagues
        except Exception as e:
            print(f"[Sleeper API] Error getting leagues for {season}: {e}", flush=True)
            return []

    async def get_league_settings(self, league_id: str) -> dict:
        """Get league settings."""
        data = await self._get(f"league/{league_id}")

        return {
            "league_id": data.get("league_id"),
            "name": data.get("name", "Unknown League"),
            "season": data.get("season"),
            "total_rosters": data.get("total_rosters", 0),
            "status": data.get("status"),
            "sport": data.get("sport"),
            "previous_league_id": data.get("previous_league_id"),
            "playoff_week_start": data.get("settings", {}).get("playoff_week_start", 15),
            "scoring_type": data.get("scoring_settings", {}),
        }

    async def get_league_users(self, league_id: str) -> List[dict]:
        """Get users/managers in a league."""
        users_data = await self._get(f"league/{league_id}/users")

        users = []
        for user in users_data:
            users.append({
                "user_id": user.get("user_id"),
                "display_name": user.get("display_name", user.get("username", "Unknown")),
                "team_name": user.get("metadata", {}).get("team_name", ""),
            })

        return users

    async def get_league_rosters(self, league_id: str) -> List[dict]:
        """Get rosters with W/L/points for all teams in a league."""
        rosters_data = await self._get(f"league/{league_id}/rosters")

        rosters = []
        for roster in rosters_data:
            settings = roster.get("settings", {})

            # Calculate total points (fpts is integer part, fpts_decimal is decimal part)
            fpts = settings.get("fpts", 0) or 0
            fpts_decimal = settings.get("fpts_decimal", 0) or 0
            points_for = float(fpts) + (float(fpts_decimal) / 100.0)

            # Same for points against
            fpts_against = settings.get("fpts_against", 0) or 0
            fpts_against_decimal = settings.get("fpts_against_decimal", 0) or 0
            points_against = float(fpts_against) + (float(fpts_against_decimal) / 100.0)

            rosters.append({
                "roster_id": roster.get("roster_id"),
                "owner_id": roster.get("owner_id"),
                "wins": settings.get("wins", 0),
                "losses": settings.get("losses", 0),
                "ties": settings.get("ties", 0),
                "points_for": points_for,
                "points_against": points_against,
                "players": roster.get("players", []),
            })

        return rosters

    async def get_matchups(self, league_id: str, week: int) -> List[dict]:
        """Get matchups for a specific week."""
        try:
            matchups_data = await self._get(f"league/{league_id}/matchups/{week}")

            if not matchups_data:
                return []

            # Group matchups by matchup_id
            matchup_groups = {}
            for matchup in matchups_data:
                matchup_id = matchup.get("matchup_id")
                if matchup_id is None:
                    continue

                if matchup_id not in matchup_groups:
                    matchup_groups[matchup_id] = []
                matchup_groups[matchup_id].append(matchup)

            # Build matchup pairs
            result = []
            for matchup_id, teams in matchup_groups.items():
                if len(teams) >= 2:
                    t1, t2 = teams[0], teams[1]
                    result.append({
                        "matchup_id": matchup_id,
                        "week": week,
                        "team1": {
                            "roster_id": t1.get("roster_id"),
                            "points": t1.get("points", 0) or 0,
                        },
                        "team2": {
                            "roster_id": t2.get("roster_id"),
                            "points": t2.get("points", 0) or 0,
                        },
                    })

            return result
        except Exception:
            return []

    async def get_transactions(self, league_id: str, round_num: int) -> List[dict]:
        """Get transactions for a specific round/week."""
        try:
            txns_data = await self._get(f"league/{league_id}/transactions/{round_num}")

            if not txns_data:
                return []

            transactions = []
            for txn in txns_data:
                txn_type = txn.get("type")  # trade, free_agent, waiver

                transactions.append({
                    "transaction_id": txn.get("transaction_id"),
                    "type": txn_type,
                    "status": txn.get("status"),
                    "created": txn.get("created"),
                    "roster_ids": txn.get("roster_ids", []),
                    "adds": txn.get("adds"),  # {player_id: roster_id}
                    "drops": txn.get("drops"),  # {player_id: roster_id}
                    "draft_picks": txn.get("draft_picks", []),
                    "waiver_budget": txn.get("waiver_budget", []),
                })

            return transactions
        except Exception as e:
            print(f"[Sleeper API] Error getting transactions for round {round_num}: {e}", flush=True)
            return []

    async def get_league_teams(self, league_id: str) -> dict:
        """Get teams in a league (combines rosters with user info)."""
        users = await self.get_league_users(league_id)
        rosters = await self.get_league_rosters(league_id)

        # Map user_id to user info
        user_map = {u["user_id"]: u for u in users}

        teams = {}
        for roster in rosters:
            roster_id = roster["roster_id"]
            owner_id = roster.get("owner_id")
            user_info = user_map.get(owner_id, {})

            display_name = user_info.get("display_name", "Unknown")
            team_name = user_info.get("team_name", "") or f"Team {roster_id}"

            # Use roster_id as team_key (similar to Yahoo's team_key)
            team_key = str(roster_id)
            teams[team_key] = {
                "team_key": team_key,
                "roster_id": roster_id,
                "owner_id": owner_id,
                "name": team_name,
                "manager": display_name,
            }

        return teams

    async def get_league_standings(self, league_id: str) -> List[dict]:
        """Get league standings."""
        users = await self.get_league_users(league_id)
        rosters = await self.get_league_rosters(league_id)

        # Map user_id to user info
        user_map = {u["user_id"]: u for u in users}

        standings = []
        for roster in rosters:
            roster_id = roster["roster_id"]
            owner_id = roster.get("owner_id")
            user_info = user_map.get(owner_id, {})

            display_name = user_info.get("display_name", "Unknown")
            team_name = user_info.get("team_name", "") or f"Team {roster_id}"

            standings.append({
                "team_key": str(roster_id),
                "name": team_name,
                "manager": display_name,
                "wins": roster.get("wins", 0),
                "losses": roster.get("losses", 0),
                "ties": roster.get("ties", 0),
                "points_for": roster.get("points_for", 0),
                "points_against": roster.get("points_against", 0),
                "rank": 0,  # Will be calculated
            })

        # Sort by wins (desc), then points_for (desc) and assign ranks
        standings.sort(key=lambda x: (-x["wins"], -x["points_for"]))
        for i, team in enumerate(standings):
            team["rank"] = i + 1

        return standings


async def lookup_user(username: str) -> Optional[SleeperUser]:
    """Lookup a Sleeper user by username."""
    url = f"https://api.sleeper.app/v1/user/{username}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        return SleeperUser(
            user_id=data.get("user_id"),
            username=data.get("username", username),
            display_name=data.get("display_name", data.get("username", username)),
        )


async def discover_league_history(api: SleeperFantasyAPI, initial_league_id: str) -> Tuple[List[Tuple[str, int]], str]:
    """
    Discover all historical seasons for a league by tracing the previous_league_id chain.

    Returns:
        tuple: (list of (league_id, year) tuples, league_name)
    """
    # Get initial league settings
    try:
        settings = await api.get_league_settings(initial_league_id)
        league_name = settings.get("name", "Unknown League")
        initial_season = int(settings.get("season", datetime.now().year))
        print(f"[HISTORY] Starting league: {league_name} ({initial_league_id})", flush=True)
    except Exception as e:
        print(f"[HISTORY] Error getting initial settings: {e}", flush=True)
        league_name = "Fantasy Football League"
        initial_season = datetime.now().year
        settings = {}

    found_leagues = [(initial_league_id, initial_season)]

    # Trace backwards using previous_league_id
    current_id = initial_league_id
    current_settings = settings

    while True:
        prev_id = current_settings.get("previous_league_id")
        if not prev_id:
            print(f"[HISTORY] No more previous_league_id", flush=True)
            break

        try:
            prev_settings = await api.get_league_settings(prev_id)
            prev_season = int(prev_settings.get("season", 0))

            if prev_season == 0:
                print(f"[HISTORY] Could not determine season for {prev_id}", flush=True)
                break

            print(f"[HISTORY] Found previous season: {prev_season} -> {prev_id}", flush=True)

            found_leagues.append((prev_id, prev_season))
            current_id = prev_id
            current_settings = prev_settings

        except Exception as e:
            print(f"[HISTORY] Error tracing previous_league_id chain: {e}", flush=True)
            break

    # Sort by year (oldest first)
    found_leagues.sort(key=lambda x: x[1])

    print(f"[HISTORY] Found {len(found_leagues)} seasons: {[y for _, y in found_leagues]}", flush=True)

    return found_leagues, league_name
