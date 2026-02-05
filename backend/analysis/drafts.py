"""Draft analysis - evaluate draft outcomes, steals, and busts."""

import pandas as pd
import numpy as np


def get_draft_grades(drafts_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate draft grades based on total points from drafted players.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column

    Returns:
        DataFrame with draft grades per team per season
    """
    if drafts_df.empty or "season_points" not in drafts_df.columns:
        return pd.DataFrame()

    drafts = drafts_df.copy()

    # Sum points by team and season
    grades = drafts.groupby(["season", "team_name"]).agg({
        "season_points": "sum",
        "pick": "count",
    }).reset_index()

    grades.columns = ["season", "team_name", "total_drafted_points", "picks"]
    grades["avg_points_per_pick"] = grades["total_drafted_points"] / grades["picks"]

    # Rank within each season
    grades["draft_rank"] = grades.groupby("season")["total_drafted_points"].rank(
        ascending=False
    )

    return grades.sort_values(["season", "draft_rank"], ascending=[False, True])


def get_best_drafts(drafts_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get the best draft classes by total points.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column
        top_n: Number of drafts to return

    Returns:
        DataFrame of best drafts
    """
    grades = get_draft_grades(drafts_df)

    if grades.empty:
        return pd.DataFrame()

    return grades.nlargest(top_n, "total_drafted_points").reset_index(drop=True)


def get_worst_drafts(drafts_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get the worst draft classes by total points.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column
        top_n: Number of drafts to return

    Returns:
        DataFrame of worst drafts
    """
    grades = get_draft_grades(drafts_df)

    if grades.empty:
        return pd.DataFrame()

    return grades.nsmallest(top_n, "total_drafted_points").reset_index(drop=True)


def get_draft_steals(drafts_df: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    """Get draft steals - players who produced far above their draft position.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with value_over_expected column
        top_n: Number of steals to return

    Returns:
        DataFrame of biggest draft steals
    """
    if drafts_df.empty or "value_over_expected" not in drafts_df.columns:
        return pd.DataFrame()

    steals = drafts_df.nlargest(top_n, "value_over_expected")[
        ["season", "team_name", "player_name", "position", "pick", "round",
         "season_points", "expected_points", "value_over_expected"]
    ]

    return steals.reset_index(drop=True)


def get_draft_busts(drafts_df: pd.DataFrame, top_n: int = 25) -> pd.DataFrame:
    """Get draft busts - players who produced far below their draft position.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with value_over_expected column
        top_n: Number of busts to return

    Returns:
        DataFrame of biggest draft busts
    """
    if drafts_df.empty or "value_over_expected" not in drafts_df.columns:
        return pd.DataFrame()

    # Only consider early-round picks as potential busts
    early_picks = drafts_df[drafts_df["round"] <= 5]

    busts = early_picks.nsmallest(top_n, "value_over_expected")[
        ["season", "team_name", "player_name", "position", "pick", "round",
         "season_points", "expected_points", "value_over_expected"]
    ]

    return busts.reset_index(drop=True)


def get_round_performance(drafts_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze draft performance by round.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column

    Returns:
        DataFrame with average production by round
    """
    if drafts_df.empty or "season_points" not in drafts_df.columns:
        return pd.DataFrame()

    round_stats = drafts_df.groupby("round").agg({
        "season_points": ["mean", "median", "std", "max"],
        "pick": "count",
    }).reset_index()

    round_stats.columns = [
        "round", "avg_points", "median_points", "std_dev", "max_points", "total_picks"
    ]

    return round_stats


def get_position_draft_value(drafts_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze draft value by position.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column

    Returns:
        DataFrame with draft value by position
    """
    if drafts_df.empty or "season_points" not in drafts_df.columns:
        return pd.DataFrame()

    position_stats = drafts_df.groupby("position").agg({
        "season_points": ["sum", "mean", "count"],
        "pick": "mean",
    }).reset_index()

    position_stats.columns = [
        "position", "total_points", "avg_points", "times_drafted", "avg_draft_position"
    ]

    return position_stats.sort_values("total_points", ascending=False).reset_index(drop=True)


def get_first_round_performance(drafts_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze first round pick performance.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column

    Returns:
        DataFrame with first round pick analysis
    """
    if drafts_df.empty or "season_points" not in drafts_df.columns:
        return pd.DataFrame()

    first_round = drafts_df[drafts_df["round"] == 1].copy()

    return first_round[
        ["season", "pick", "team_name", "player_name", "position", "season_points"]
    ].sort_values(["season", "pick"])


def get_team_draft_history(drafts_df: pd.DataFrame) -> pd.DataFrame:
    """Get aggregate draft performance by team across all seasons.

    Args:
        drafts_df: DataFrame from fetch_all_drafts with season_points column

    Returns:
        DataFrame with team draft history
    """
    if drafts_df.empty or "season_points" not in drafts_df.columns:
        return pd.DataFrame()

    team_history = drafts_df.groupby("team_name").agg({
        "season_points": ["sum", "mean"],
        "season": "nunique",
        "pick": "count",
    }).reset_index()

    team_history.columns = [
        "team_name", "total_points", "avg_points_per_pick", "seasons_drafted", "total_picks"
    ]

    # Calculate rank
    team_history["draft_rank"] = team_history["total_points"].rank(ascending=False)

    return team_history.sort_values("total_points", ascending=False).reset_index(drop=True)
