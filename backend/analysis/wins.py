"""Win/loss record and streak analysis."""

import pandas as pd
from ..data.matchups import get_team_scores_by_week


def get_season_win_leaders(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get win totals for each team by season.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with season, team_name, wins, losses, win_pct
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]  # Regular season only

    season_records = team_scores.groupby(["season", "team_name"]).agg({
        "won": "sum",
        "week": "count",
    }).reset_index()

    season_records.columns = ["season", "team_name", "wins", "games"]
    season_records["losses"] = season_records["games"] - season_records["wins"]
    season_records["win_pct"] = season_records["wins"] / season_records["games"]

    # Rank within each season
    season_records["season_rank"] = season_records.groupby("season")["wins"].rank(
        ascending=False, method="min"
    )

    return season_records.sort_values(["season", "wins"], ascending=[False, False])


def get_alltime_win_leaders(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get all-time win totals by team.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with team_name, wins, losses, win_pct, seasons
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    alltime = team_scores.groupby("team_name").agg({
        "won": "sum",
        "week": "count",
        "season": "nunique",
    }).reset_index()

    alltime.columns = ["team_name", "wins", "games", "seasons"]
    alltime["losses"] = alltime["games"] - alltime["wins"]
    alltime["win_pct"] = alltime["wins"] / alltime["games"]

    return alltime.sort_values("wins", ascending=False).reset_index(drop=True)


def get_worst_teams_by_season(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get the worst team for each season (fewest wins) with scoring stats.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with one row per season showing the worst team with scoring
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    # Get full stats per team/season
    season_stats = team_scores.groupby(["season", "team_name"]).agg({
        "won": "sum",
        "week": "count",
        "points_for": ["sum", "mean"],
    }).reset_index()

    season_stats.columns = ["season", "team_name", "wins", "games", "total_pts", "avg_ppg"]
    season_stats["losses"] = season_stats["games"] - season_stats["wins"]
    season_stats["win_pct"] = season_stats["wins"] / season_stats["games"]

    # Calculate median PPG per season
    season_median = season_stats.groupby("season")["avg_ppg"].median().reset_index()
    season_median.columns = ["season", "median_ppg"]

    season_stats = season_stats.merge(season_median, on="season")
    season_stats["ppg_vs_median"] = season_stats["avg_ppg"] - season_stats["median_ppg"]

    # Get worst team per season (fewest wins)
    worst_per_season = season_stats.loc[
        season_stats.groupby("season")["wins"].idxmin()
    ]

    return worst_per_season[
        ["season", "team_name", "wins", "losses", "total_pts", "avg_ppg", "ppg_vs_median"]
    ].sort_values("season", ascending=False).reset_index(drop=True)


def get_best_teams_by_season(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get the best team for each season (most wins).

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with one row per season showing the best team
    """
    season_records = get_season_win_leaders(matchups_df)

    best_per_season = season_records.loc[
        season_records.groupby("season")["wins"].idxmax()
    ]

    return best_per_season[
        ["season", "team_name", "wins", "losses", "win_pct"]
    ].reset_index(drop=True)


def calculate_streaks(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate win and loss streaks for all teams.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with streak information for each team
    """
    team_scores = get_team_scores_by_week(matchups_df)

    # Sort by team and chronological order
    team_scores = team_scores.sort_values(["team_name", "season", "week"])

    all_streaks = []

    for team_name in team_scores["team_name"].unique():
        team_games = team_scores[team_scores["team_name"] == team_name].copy()

        # Calculate streaks
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0

        win_streak_details = None
        loss_streak_details = None

        for i, (_, game) in enumerate(team_games.iterrows()):
            if game["won"]:
                current_win_streak += 1
                current_loss_streak = 0
                if current_win_streak > max_win_streak:
                    max_win_streak = current_win_streak
                    win_streak_details = {
                        "end_season": game["season"],
                        "end_week": game["week"],
                    }
            else:
                current_loss_streak += 1
                current_win_streak = 0
                if current_loss_streak > max_loss_streak:
                    max_loss_streak = current_loss_streak
                    loss_streak_details = {
                        "end_season": game["season"],
                        "end_week": game["week"],
                    }

        all_streaks.append({
            "team_name": team_name,
            "max_win_streak": max_win_streak,
            "win_streak_end_season": win_streak_details["end_season"] if win_streak_details else None,
            "win_streak_end_week": win_streak_details["end_week"] if win_streak_details else None,
            "max_loss_streak": max_loss_streak,
            "loss_streak_end_season": loss_streak_details["end_season"] if loss_streak_details else None,
            "loss_streak_end_week": loss_streak_details["end_week"] if loss_streak_details else None,
        })

    return pd.DataFrame(all_streaks)


def get_longest_win_streaks(matchups_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get the longest win streaks across all teams.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of streaks to return

    Returns:
        DataFrame of top win streaks
    """
    streaks = calculate_streaks(matchups_df)
    return streaks.nlargest(top_n, "max_win_streak")[
        ["team_name", "max_win_streak", "win_streak_end_season", "win_streak_end_week"]
    ].reset_index(drop=True)


def get_longest_loss_streaks(matchups_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get the longest losing streaks across all teams.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of streaks to return

    Returns:
        DataFrame of top losing streaks
    """
    streaks = calculate_streaks(matchups_df)
    return streaks.nlargest(top_n, "max_loss_streak")[
        ["team_name", "max_loss_streak", "loss_streak_end_season", "loss_streak_end_week"]
    ].reset_index(drop=True)
