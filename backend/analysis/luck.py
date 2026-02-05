"""Luck analysis - unlucky losses, lucky wins, all-play records."""

import pandas as pd
import numpy as np
from ..data.matchups import get_team_scores_by_week


def get_weekly_median_scores(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate median score for each week.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with season, week, median_score
    """
    team_scores = get_team_scores_by_week(matchups_df)

    weekly_medians = team_scores.groupby(["season", "week"])["points_for"].median().reset_index()
    weekly_medians.columns = ["season", "week", "median_score"]

    return weekly_medians


def get_unlucky_losses(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
) -> pd.DataFrame:
    """Find losses where the team scored above the weekly median.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of unlucky losses to return

    Returns:
        DataFrame with unlucky loss details
    """
    team_scores = get_team_scores_by_week(matchups_df)
    weekly_medians = get_weekly_median_scores(matchups_df)

    # Merge to get median for each game
    merged = team_scores.merge(weekly_medians, on=["season", "week"])

    # Find losses where team scored above median
    unlucky = merged[
        (~merged["won"]) & (merged["points_for"] > merged["median_score"])
    ].copy()

    # Calculate how much above median they scored
    unlucky["above_median"] = unlucky["points_for"] - unlucky["median_score"]

    # Sort by how unlucky (most points in a loss)
    unlucky = unlucky.nlargest(top_n, "points_for")[
        ["season", "week", "team_name", "points_for", "opponent_name", "points_against", "median_score"]
    ]

    return unlucky.reset_index(drop=True)


def get_lucky_wins(
    matchups_df: pd.DataFrame,
    top_n: int = 25,
) -> pd.DataFrame:
    """Find wins where the team scored below the weekly median.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of lucky wins to return

    Returns:
        DataFrame with lucky win details
    """
    team_scores = get_team_scores_by_week(matchups_df)
    weekly_medians = get_weekly_median_scores(matchups_df)

    merged = team_scores.merge(weekly_medians, on=["season", "week"])

    # Find wins where team scored below median
    lucky = merged[
        (merged["won"]) & (merged["points_for"] < merged["median_score"])
    ].copy()

    # Calculate how much below median they scored
    lucky["below_median"] = lucky["median_score"] - lucky["points_for"]

    # Sort by how lucky (fewest points in a win)
    lucky = lucky.nsmallest(top_n, "points_for")[
        ["season", "week", "team_name", "points_for", "opponent_name", "points_against", "median_score"]
    ]

    return lucky.reset_index(drop=True)


def calculate_all_play_records(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all-play records (what if you played everyone each week).

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with all-play wins, losses, and win percentage
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]  # Regular season only

    all_play_records = []

    for (season, week), week_scores in team_scores.groupby(["season", "week"]):
        scores = week_scores["points_for"].values
        team_names = week_scores["team_name"].values

        for i, (team, score) in enumerate(zip(team_names, scores)):
            # Count wins against all other teams this week
            wins = sum(score > other for j, other in enumerate(scores) if i != j)
            losses = sum(score < other for j, other in enumerate(scores) if i != j)
            ties = sum(score == other for j, other in enumerate(scores) if i != j)

            all_play_records.append({
                "season": season,
                "week": week,
                "team_name": team,
                "all_play_wins": wins,
                "all_play_losses": losses,
                "all_play_ties": ties,
            })

    records_df = pd.DataFrame(all_play_records)

    # Aggregate by team and season
    season_all_play = records_df.groupby(["season", "team_name"]).agg({
        "all_play_wins": "sum",
        "all_play_losses": "sum",
        "all_play_ties": "sum",
    }).reset_index()

    season_all_play["all_play_games"] = (
        season_all_play["all_play_wins"] +
        season_all_play["all_play_losses"] +
        season_all_play["all_play_ties"]
    )
    season_all_play["all_play_win_pct"] = (
        season_all_play["all_play_wins"] / season_all_play["all_play_games"]
    )

    return season_all_play.sort_values(["season", "all_play_win_pct"], ascending=[False, False])


def get_alltime_all_play_records(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all-time all-play records aggregated across all seasons.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with all-time all-play wins, losses, and win percentage by manager
    """
    season_all_play = calculate_all_play_records(matchups_df)

    # Aggregate across all seasons
    alltime = season_all_play.groupby("team_name").agg({
        "all_play_wins": "sum",
        "all_play_losses": "sum",
        "all_play_ties": "sum",
    }).reset_index()

    alltime["all_play_games"] = (
        alltime["all_play_wins"] +
        alltime["all_play_losses"] +
        alltime["all_play_ties"]
    )
    alltime["all_play_win_pct"] = (
        alltime["all_play_wins"] / alltime["all_play_games"]
    )

    # Count seasons
    seasons_count = season_all_play.groupby("team_name")["season"].nunique().reset_index()
    seasons_count.columns = ["team_name", "seasons"]
    alltime = alltime.merge(seasons_count, on="team_name")

    return alltime.sort_values("all_play_win_pct", ascending=False).reset_index(drop=True)


def get_luck_index(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate luck index comparing actual record to all-play record.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with luck index for each team/season
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    # Actual records
    actual = team_scores.groupby(["season", "team_name"]).agg({
        "won": "sum",
        "week": "count",
    }).reset_index()
    actual.columns = ["season", "team_name", "actual_wins", "games"]
    actual["actual_win_pct"] = actual["actual_wins"] / actual["games"]

    # All-play records
    all_play = calculate_all_play_records(matchups_df)

    # Merge
    merged = actual.merge(
        all_play[["season", "team_name", "all_play_win_pct"]],
        on=["season", "team_name"],
    )

    # Luck index = actual win % - all-play win %
    # Positive = lucky (won more than expected)
    # Negative = unlucky (won less than expected)
    merged["luck_index"] = merged["actual_win_pct"] - merged["all_play_win_pct"]

    return merged.sort_values("luck_index", ascending=True)


def get_unluckiest_teams(matchups_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get teams with the worst luck index.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of teams to return

    Returns:
        DataFrame of unluckiest team seasons
    """
    luck = get_luck_index(matchups_df)
    return luck.head(top_n).reset_index(drop=True)


def get_luckiest_teams(matchups_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Get teams with the best luck index.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        top_n: Number of teams to return

    Returns:
        DataFrame of luckiest team seasons
    """
    luck = get_luck_index(matchups_df)
    return luck.tail(top_n).sort_values("luck_index", ascending=False).reset_index(drop=True)


def get_points_against_analysis(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze points against for each team (schedule luck indicator).

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with points against stats and league rank
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    pa_stats = team_scores.groupby(["season", "team_name"]).agg({
        "points_against": ["sum", "mean"],
        "points_for": "sum",
        "won": "sum",
    }).reset_index()

    pa_stats.columns = [
        "season", "team_name", "total_pa", "avg_pa", "total_pf", "wins"
    ]

    # Rank by points against within each season
    pa_stats["pa_rank"] = pa_stats.groupby("season")["total_pa"].rank(ascending=True)

    return pa_stats.sort_values(["season", "total_pa"], ascending=[False, True])


def get_points_against_leaders_by_year(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get the team with most points scored against them for each year.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with one row per season showing who had most PA
    """
    team_scores = get_team_scores_by_week(matchups_df)
    team_scores = team_scores[~team_scores["is_playoff"]]

    pa_stats = team_scores.groupby(["season", "team_name"]).agg({
        "points_against": ["sum", "mean"],
        "won": "sum",
        "week": "count",
    }).reset_index()

    pa_stats.columns = [
        "season", "team_name", "total_pa", "avg_pa", "wins", "games"
    ]

    # Get max PA per season
    idx = pa_stats.groupby("season")["total_pa"].idxmax()
    leaders = pa_stats.loc[idx].copy()

    # Calculate league average PA for context
    season_avg = pa_stats.groupby("season")["total_pa"].mean().reset_index()
    season_avg.columns = ["season", "league_avg_pa"]

    leaders = leaders.merge(season_avg, on="season")
    leaders["pa_vs_avg"] = leaders["total_pa"] - leaders["league_avg_pa"]

    return leaders.sort_values("season", ascending=False).reset_index(drop=True)
