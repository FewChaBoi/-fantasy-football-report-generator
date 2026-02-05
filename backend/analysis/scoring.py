"""Scoring analysis - weekly highs, season totals, all-time leaders."""

import pandas as pd
from ..data.matchups import get_team_scores_by_week


def get_weekly_high_scores(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
    include_playoffs: bool = True,
) -> pd.DataFrame:
    """Get the highest scoring single-week performances.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of top scores to return
        include_playoffs: Whether to include playoff weeks

    Returns:
        DataFrame with season, week, team_name, points_for, opponent, won
    """
    team_scores = get_team_scores_by_week(matchups_df)

    if not include_playoffs:
        team_scores = team_scores[~team_scores["is_playoff"]]

    top_scores = team_scores.nlargest(top_n, "points_for")[
        ["season", "week", "team_name", "points_for", "opponent_name", "won", "is_playoff"]
    ]

    return top_scores.reset_index(drop=True)


def get_weekly_low_scores(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
    include_playoffs: bool = True,
) -> pd.DataFrame:
    """Get the lowest scoring single-week performances.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of scores to return
        include_playoffs: Whether to include playoff weeks

    Returns:
        DataFrame with season, week, team_name, points_for, opponent, won
    """
    team_scores = get_team_scores_by_week(matchups_df)

    if not include_playoffs:
        team_scores = team_scores[~team_scores["is_playoff"]]

    # Filter out zero scores (likely incomplete weeks)
    team_scores = team_scores[team_scores["points_for"] > 0]

    low_scores = team_scores.nsmallest(top_n, "points_for")[
        ["season", "week", "team_name", "points_for", "opponent_name", "won", "is_playoff"]
    ]

    return low_scores.reset_index(drop=True)


def get_season_scoring_leaders(
    matchups_df: pd.DataFrame,
    include_playoffs: bool = False,
) -> pd.DataFrame:
    """Get total points for each team by season.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        include_playoffs: Whether to include playoff points

    Returns:
        DataFrame with season, team_name, total_points, games, ppg
    """
    team_scores = get_team_scores_by_week(matchups_df)

    if not include_playoffs:
        team_scores = team_scores[~team_scores["is_playoff"]]

    season_totals = team_scores.groupby(["season", "team_name"]).agg({
        "points_for": "sum",
        "week": "count",
    }).reset_index()

    season_totals.columns = ["season", "team_name", "total_points", "games"]
    season_totals["ppg"] = season_totals["total_points"] / season_totals["games"]

    # Rank within each season
    season_totals["season_rank"] = season_totals.groupby("season")["total_points"].rank(
        ascending=False
    )

    return season_totals.sort_values(["season", "total_points"], ascending=[False, False])


def get_alltime_scoring_leaders(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get all-time total points by team.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with team_name, total_points, games, ppg, seasons
    """
    team_scores = get_team_scores_by_week(matchups_df)

    # Regular season only for fair comparison
    team_scores = team_scores[~team_scores["is_playoff"]]

    alltime = team_scores.groupby("team_name").agg({
        "points_for": "sum",
        "week": "count",
        "season": "nunique",
    }).reset_index()

    alltime.columns = ["team_name", "total_points", "games", "seasons"]
    alltime["ppg"] = alltime["total_points"] / alltime["games"]

    return alltime.sort_values("total_points", ascending=False).reset_index(drop=True)


def get_season_high_scorers(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get the highest scoring team for each season.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with one row per season showing the top scorer
    """
    season_leaders = get_season_scoring_leaders(matchups_df, include_playoffs=False)
    top_per_season = season_leaders[season_leaders["season_rank"] == 1]

    return top_per_season[["season", "team_name", "total_points", "ppg"]].reset_index(drop=True)


def get_points_for_vs_against(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get points for and against comparison for each team by season.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with team stats and point differential
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    summary = team_scores.groupby(["season", "team_name"]).agg({
        "points_for": "sum",
        "points_against": "sum",
        "won": "sum",
        "week": "count",
    }).reset_index()

    summary.columns = ["season", "team_name", "points_for", "points_against", "wins", "games"]
    summary["point_diff"] = summary["points_for"] - summary["points_against"]
    summary["ppg_for"] = summary["points_for"] / summary["games"]
    summary["ppg_against"] = summary["points_against"] / summary["games"]

    return summary.sort_values(["season", "points_for"], ascending=[False, False])


def get_yearly_scoring_totals(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get total points scored by each manager for each year.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with season, team_name, total_points for charting
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    yearly = team_scores.groupby(["season", "team_name"]).agg({
        "points_for": "sum",
    }).reset_index()

    yearly.columns = ["season", "team_name", "total_points"]

    return yearly.sort_values(["season", "team_name"])
