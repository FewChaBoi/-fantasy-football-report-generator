"""Consistency analysis - variance in team scoring."""

import pandas as pd
import numpy as np
from ..data.matchups import get_team_scores_by_week


def calculate_scoring_variance(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate scoring variance for each team by season.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with variance metrics per team per season
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]  # Regular season only

    variance_stats = team_scores.groupby(["season", "team_name"]).agg({
        "points_for": ["mean", "std", "min", "max", "count"],
    }).reset_index()

    variance_stats.columns = [
        "season", "team_name", "avg_score", "std_dev", "min_score", "max_score", "games"
    ]

    # Calculate coefficient of variation (CV) - normalized measure of variance
    variance_stats["cv"] = variance_stats["std_dev"] / variance_stats["avg_score"]

    # Score range
    variance_stats["score_range"] = variance_stats["max_score"] - variance_stats["min_score"]

    return variance_stats.sort_values(["season", "cv"], ascending=[False, True])


def get_most_consistent_teams(
    matchups_df: pd.DataFrame,
    top_n: int = 15,
) -> pd.DataFrame:
    """Get the most consistent scoring teams (lowest variance).

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of teams to return

    Returns:
        DataFrame of most consistent team-seasons
    """
    variance = calculate_scoring_variance(matchups_df)

    if variance.empty:
        return pd.DataFrame()

    # Most consistent = lowest coefficient of variation
    consistent = variance.nsmallest(top_n, "cv")[
        ["season", "team_name", "avg_score", "std_dev", "cv", "min_score", "max_score"]
    ]

    return consistent.reset_index(drop=True)


def get_most_volatile_teams(
    matchups_df: pd.DataFrame,
    top_n: int = 15,
) -> pd.DataFrame:
    """Get the most volatile (boom or bust) teams (highest variance).

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of teams to return

    Returns:
        DataFrame of most volatile team-seasons
    """
    variance = calculate_scoring_variance(matchups_df)

    if variance.empty:
        return pd.DataFrame()

    # Most volatile = highest coefficient of variation
    volatile = variance.nlargest(top_n, "cv")[
        ["season", "team_name", "avg_score", "std_dev", "cv", "min_score", "max_score"]
    ]

    return volatile.reset_index(drop=True)


def get_consistency_rankings(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get consistency rankings for all teams across all seasons.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with consistency rankings
    """
    variance = calculate_scoring_variance(matchups_df)

    if variance.empty:
        return pd.DataFrame()

    # Rank within each season
    variance["consistency_rank"] = variance.groupby("season")["cv"].rank(ascending=True)

    return variance.sort_values(["season", "consistency_rank"])


def get_alltime_consistency(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get all-time consistency metrics by team.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with all-time consistency per team
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    alltime = team_scores.groupby("team_name").agg({
        "points_for": ["mean", "std", "min", "max", "count"],
        "season": "nunique",
    }).reset_index()

    alltime.columns = [
        "team_name", "avg_score", "std_dev", "min_score", "max_score", "total_games", "seasons"
    ]

    alltime["cv"] = alltime["std_dev"] / alltime["avg_score"]
    alltime["score_range"] = alltime["max_score"] - alltime["min_score"]

    return alltime.sort_values("cv", ascending=True).reset_index(drop=True)


def get_boom_bust_analysis(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze boom and bust games for each team.

    A "boom" is scoring 20%+ above average.
    A "bust" is scoring 20%+ below average.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with boom/bust counts per team
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    # Calculate each team's average
    team_avgs = team_scores.groupby("team_name")["points_for"].mean().to_dict()

    team_scores["team_avg"] = team_scores["team_name"].map(team_avgs)
    team_scores["pct_of_avg"] = team_scores["points_for"] / team_scores["team_avg"]

    # Define boom and bust thresholds
    team_scores["is_boom"] = team_scores["pct_of_avg"] >= 1.20
    team_scores["is_bust"] = team_scores["pct_of_avg"] <= 0.80

    boom_bust = team_scores.groupby("team_name").agg({
        "is_boom": "sum",
        "is_bust": "sum",
        "points_for": "count",
    }).reset_index()

    boom_bust.columns = ["team_name", "boom_games", "bust_games", "total_games"]
    boom_bust["boom_pct"] = boom_bust["boom_games"] / boom_bust["total_games"] * 100
    boom_bust["bust_pct"] = boom_bust["bust_games"] / boom_bust["total_games"] * 100
    boom_bust["volatility_score"] = boom_bust["boom_pct"] + boom_bust["bust_pct"]

    return boom_bust.sort_values("volatility_score", ascending=False).reset_index(drop=True)


def get_scoring_distribution(matchups_df: pd.DataFrame, team_name: str = None) -> pd.DataFrame:
    """Get scoring distribution for analysis.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        team_name: Optional specific team to analyze

    Returns:
        DataFrame with scoring percentiles
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    if team_name:
        team_scores = team_scores[team_scores["team_name"] == team_name]

    if team_scores.empty:
        return pd.DataFrame()

    percentiles = [10, 25, 50, 75, 90]
    result = team_scores.groupby("team_name")["points_for"].describe(
        percentiles=[p/100 for p in percentiles]
    ).reset_index()

    return result
