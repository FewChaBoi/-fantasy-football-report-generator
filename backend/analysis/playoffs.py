"""Playoff and championship analysis."""

import pandas as pd
from .helpers import get_team_scores_by_week


def get_playoff_appearances(standings_df: pd.DataFrame) -> pd.DataFrame:
    """Get playoff appearance counts by team.

    Args:
        standings_df: DataFrame from fetch_all_standings

    Returns:
        DataFrame with team_name, appearances, seasons_played, appearance_pct
    """
    if standings_df.empty:
        return pd.DataFrame()

    appearances = standings_df.groupby("team_name").agg({
        "made_playoffs": "sum",
        "season": "count",
    }).reset_index()

    appearances.columns = ["team_name", "playoff_appearances", "seasons_played"]
    appearances["appearance_pct"] = (
        appearances["playoff_appearances"] / appearances["seasons_played"]
    )

    return appearances.sort_values("playoff_appearances", ascending=False).reset_index(drop=True)


def get_championship_counts(standings_df: pd.DataFrame) -> pd.DataFrame:
    """Get championship wins and finals appearances by team.

    Args:
        standings_df: DataFrame from fetch_all_standings with championship info

    Returns:
        DataFrame with team_name, championships, finals_appearances, conversion_rate
    """
    if standings_df.empty or "won_championship" not in standings_df.columns:
        return pd.DataFrame()

    champs = standings_df.groupby("team_name").agg({
        "won_championship": "sum",
        "finals_appearance": "sum",
        "season": "count",
    }).reset_index()

    champs.columns = ["team_name", "championships", "finals_appearances", "seasons"]
    champs["conversion_rate"] = champs.apply(
        lambda x: x["championships"] / x["finals_appearances"] if x["finals_appearances"] > 0 else 0,
        axis=1,
    )

    return champs.sort_values(
        ["championships", "finals_appearances"], ascending=[False, False]
    ).reset_index(drop=True)


def get_placement_counts(standings_df: pd.DataFrame) -> pd.DataFrame:
    """Get 1st, 2nd, 3rd place finishes and total podium finishes by manager.

    Args:
        standings_df: DataFrame from fetch_all_standings with rank info

    Returns:
        DataFrame with team_name, 1st, 2nd, 3rd, total_podium, seasons
    """
    if standings_df.empty or "rank" not in standings_df.columns:
        return pd.DataFrame()

    # Count placements
    standings_df = standings_df.copy()
    standings_df["first"] = (standings_df["rank"] == 1).astype(int)
    standings_df["second"] = (standings_df["rank"] == 2).astype(int)
    standings_df["third"] = (standings_df["rank"] == 3).astype(int)

    placements = standings_df.groupby("team_name").agg({
        "first": "sum",
        "second": "sum",
        "third": "sum",
        "season": "count",
    }).reset_index()

    placements.columns = ["team_name", "1st", "2nd", "3rd", "seasons"]
    placements["total_podium"] = placements["1st"] + placements["2nd"] + placements["3rd"]

    return placements.sort_values(
        ["1st", "2nd", "3rd", "total_podium"], ascending=[False, False, False, False]
    ).reset_index(drop=True)


def get_podium_by_year(standings_df: pd.DataFrame) -> pd.DataFrame:
    """Get 1st, 2nd, and 3rd place finishers for each year.

    Args:
        standings_df: DataFrame from fetch_all_standings with rank info

    Returns:
        DataFrame with season, 1st place, 2nd place, 3rd place
    """
    if standings_df.empty or "rank" not in standings_df.columns:
        return pd.DataFrame()

    podium_data = []

    for season in sorted(standings_df["season"].unique(), reverse=True):
        season_df = standings_df[standings_df["season"] == season]

        first = season_df[season_df["rank"] == 1]["team_name"].values
        second = season_df[season_df["rank"] == 2]["team_name"].values
        third = season_df[season_df["rank"] == 3]["team_name"].values

        podium_data.append({
            "season": season,
            "1st": first[0] if len(first) > 0 else "",
            "2nd": second[0] if len(second) > 0 else "",
            "3rd": third[0] if len(third) > 0 else "",
        })

    return pd.DataFrame(podium_data)


def get_playoff_records(matchups_df: pd.DataFrame) -> pd.DataFrame:
    """Get playoff win/loss records by team.

    Args:
        matchups_df: DataFrame from fetch_all_matchups

    Returns:
        DataFrame with team playoff records
    """
    team_scores = get_team_scores_by_week(matchups_df)
    playoff_games = team_scores[team_scores["is_playoff"]]

    if playoff_games.empty:
        return pd.DataFrame()

    records = playoff_games.groupby("team_name").agg({
        "won": "sum",
        "week": "count",
    }).reset_index()

    records.columns = ["team_name", "playoff_wins", "playoff_games"]
    records["playoff_losses"] = records["playoff_games"] - records["playoff_wins"]
    records["playoff_win_pct"] = records["playoff_wins"] / records["playoff_games"]

    return records.sort_values("playoff_wins", ascending=False).reset_index(drop=True)


def get_championship_bracket_records(
    matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
) -> pd.DataFrame:
    """Get championship bracket win/loss records (teams that made playoffs).

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        standings_df: DataFrame from fetch_all_standings

    Returns:
        DataFrame with championship bracket records
    """
    team_scores = get_team_scores_by_week(matchups_df)
    playoff_games = team_scores[team_scores["is_playoff"]].copy()

    if playoff_games.empty or standings_df.empty:
        return pd.DataFrame()

    # Get teams that made playoffs each season (rank 1-6)
    playoff_teams = standings_df[standings_df["rank"] <= 6][["season", "team_name"]].copy()
    playoff_teams["in_championship"] = True

    # Merge to identify championship bracket games
    playoff_games = playoff_games.merge(
        playoff_teams,
        on=["season", "team_name"],
        how="left"
    )
    playoff_games["in_championship"] = playoff_games["in_championship"].fillna(False)

    # Championship bracket games
    champ_games = playoff_games[playoff_games["in_championship"]]

    if champ_games.empty:
        return pd.DataFrame()

    records = champ_games.groupby("team_name").agg({
        "won": "sum",
        "week": "count",
    }).reset_index()

    records.columns = ["team_name", "champ_wins", "champ_games"]
    records["champ_losses"] = records["champ_games"] - records["champ_wins"]
    records["champ_win_pct"] = records["champ_wins"] / records["champ_games"]

    return records.sort_values("champ_wins", ascending=False).reset_index(drop=True)


def get_consolation_bracket_records(
    matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
) -> pd.DataFrame:
    """Get consolation bracket win/loss records (teams that missed playoffs).

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        standings_df: DataFrame from fetch_all_standings

    Returns:
        DataFrame with consolation bracket records
    """
    team_scores = get_team_scores_by_week(matchups_df)
    playoff_games = team_scores[team_scores["is_playoff"]].copy()

    if playoff_games.empty or standings_df.empty:
        return pd.DataFrame()

    # Get teams that made playoffs each season (rank 1-6)
    playoff_teams = standings_df[standings_df["rank"] <= 6][["season", "team_name"]].copy()
    playoff_teams["in_championship"] = True

    # Merge to identify championship bracket games
    playoff_games = playoff_games.merge(
        playoff_teams,
        on=["season", "team_name"],
        how="left"
    )
    playoff_games["in_championship"] = playoff_games["in_championship"].fillna(False)

    # Consolation bracket games
    consolation_games = playoff_games[~playoff_games["in_championship"]]

    if consolation_games.empty:
        return pd.DataFrame()

    records = consolation_games.groupby("team_name").agg({
        "won": "sum",
        "week": "count",
    }).reset_index()

    records.columns = ["team_name", "consolation_wins", "consolation_games"]
    records["consolation_losses"] = records["consolation_games"] - records["consolation_wins"]
    records["consolation_win_pct"] = records["consolation_wins"] / records["consolation_games"]

    return records.sort_values("consolation_wins", ascending=False).reset_index(drop=True)


def get_regular_vs_playoff_performance(
    matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare regular season rank to playoff finish.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        standings_df: DataFrame from fetch_all_standings

    Returns:
        DataFrame comparing regular season and playoff performance
    """
    if standings_df.empty or matchups_df.empty:
        return pd.DataFrame()

    team_scores = get_team_scores_by_week(matchups_df)

    # Regular season records
    reg_season = team_scores[~team_scores["is_playoff"]]
    reg_records = reg_season.groupby(["season", "team_name"]).agg({
        "won": "sum",
        "points_for": "sum",
    }).reset_index()

    reg_records["reg_season_rank"] = reg_records.groupby("season")["won"].rank(
        ascending=False, method="min"
    )

    # Merge with standings for playoff info
    merged = reg_records.merge(
        standings_df[["season", "team_name", "made_playoffs", "won_championship", "finals_appearance"]],
        on=["season", "team_name"],
        how="left",
    )

    # Determine playoff finish
    merged["playoff_finish"] = merged.apply(
        lambda x: (
            "Champion" if x.get("won_championship", False)
            else "Finals" if x.get("finals_appearance", False)
            else "Made Playoffs" if x.get("made_playoffs", False)
            else "Missed"
        ),
        axis=1,
    )

    return merged.sort_values(["season", "reg_season_rank"]).reset_index(drop=True)


def get_underdog_champions(
    matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    min_seed: int = 4,
) -> pd.DataFrame:
    """Find champions who won from a low seed.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        standings_df: DataFrame from fetch_all_standings
        min_seed: Minimum seed to be considered an underdog

    Returns:
        DataFrame of underdog championship wins
    """
    perf = get_regular_vs_playoff_performance(matchups_df, standings_df)

    if perf.empty:
        return pd.DataFrame()

    underdogs = perf[
        (perf["playoff_finish"] == "Champion") & (perf["reg_season_rank"] >= min_seed)
    ]

    return underdogs[
        ["season", "team_name", "reg_season_rank", "won", "points_for"]
    ].reset_index(drop=True)


def get_favorites_who_failed(
    matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
) -> pd.DataFrame:
    """Find #1 seeds who didn't win the championship.

    Args:
        matchups_df: DataFrame from fetch_all_matchups
        standings_df: DataFrame from fetch_all_standings

    Returns:
        DataFrame of top seeds who failed to win it all
    """
    perf = get_regular_vs_playoff_performance(matchups_df, standings_df)

    if perf.empty:
        return pd.DataFrame()

    failed = perf[
        (perf["reg_season_rank"] == 1) & (perf["playoff_finish"] != "Champion")
    ]

    return failed[
        ["season", "team_name", "won", "points_for", "playoff_finish"]
    ].reset_index(drop=True)
