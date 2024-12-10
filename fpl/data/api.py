from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import httpx
import polars as pl
import pytz

from .config import *


def api_client() -> httpx.Client:
    """
    Returns a client for connecting to the FPL API
    """

    return httpx.Client(base_url="https://fantasy.premierleague.com/api", event_hooks={"response": [lambda x: x.raise_for_status()]})


def get_entry_history(client: httpx.Client, entry_id: int) -> pl.DataFrame:
    """
    Returns the points by week for the entry
    """

    df = (pl.DataFrame(client.get(f"entry/{entry_id}/history/").json()["current"])
          .with_columns(entry_id=entry_id)
          .rename({"event": "gameweek_id"})
          .select(["gameweek_id", "entry_id", "total_points"])
          )

    return df


def get_entry_picks(client: httpx.Client, entry_id: int, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the players picked for a gameweek
    """

    df = (pl.DataFrame(client.get(f"entry/{entry_id}/event/{gameweek_id}/picks/").json()["picks"])
          .with_columns(entry_id=entry_id)
          .rename({"element": "player_id"})
          )

    return df


def get_entry_points(client: httpx.Client, entry_id: int, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the total points for an entry at the end of a gameweek
    """

    return (pl.DataFrame(client.get(f"entry/{entry_id}/event/{gameweek_id}/picks/").json()["entry_history"])
            .with_columns(entry_id=entry_id).cast(pl.Int32)
            .select(["entry_id", "total_points"])
            )


def get_fixtures(client: httpx.Client, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the fixtures for the gameweek
    """

    from .cache import TEAMS_DF

    return (pl.DataFrame(client.get("fixtures/").json())
            .filter(pl.col("event") == gameweek_id)
            .rename({"team_a": "away_team_id", "team_a_score": "away_team_score", "team_h": "home_team_id", "team_h_score": "home_team_score"})
            .with_columns(pl.col("kickoff_time").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ").alias("kickoff_time_d"))
            .sort(pl.col("kickoff_time_d"))
            .with_columns(pl.col("kickoff_time_d").dt.strftime("%a %d %b %H:%M").alias("kickoff_time"))
            .with_columns(pl.when(pl.col("finished_provisional") == True)
                          .then(pl.lit("FT"))
                          .otherwise(pl.concat_str(pl.col("minutes"), pl.lit("'"))).alias("minutes"))
            .with_columns(pl.when(pl.col("kickoff_time_d") <= datetime.now()).then(pl.col("minutes")).otherwise(pl.col("kickoff_time")).alias("time"))
            .join(TEAMS_DF, left_on="away_team_id", right_on="team_id")
            .rename({"team_name": "away_team_name", "logo": "away_team_logo"})
            .join(TEAMS_DF, left_on="home_team_id", right_on="team_id")
            .rename({"team_name": "home_team_name", "logo": "home_team_logo"})
            .select(["id", "away_team_name", "away_team_score", "home_team_name", "home_team_score", "kickoff_time", "kickoff_time_d", "minutes", "away_team_logo", "home_team_logo", "time"])
            )


def get_gameweek() -> int:
    """
    Returns the current gameweek
    """
    from .cache import GAMEWEEKS_DF
    return GAMEWEEKS_DF.filter(pl.col("deadline_time") <= datetime.now(pytz.UTC)).sort("deadline_time", descending=True).row(0, named=True)


def get_league_picks(client: httpx.Client, gameweek_id: int, league_df: pl.DataFrame) -> pl.DataFrame:
    """
    Returns the gameweek picks for all teams in the league
    """
    from .cache import PLAYERS_DF

    with ThreadPoolExecutor() as executor:
        picks = list(executor.map(lambda entry_id: get_entry_picks(
            client, entry_id, gameweek_id), league_df["entry_id"].to_list()))

    return (pl.concat(picks)
            .join(PLAYERS_DF, on="player_id")
            .join(league_df, on="entry_id")
            .filter(pl.col("position") < 12)
            .select(["entry_id", "manager_name", "web_name", "team_name", "position_name", "player_id", "multiplier", "is_captain", "position", "img_url"])
            )


def get_league_table(client: httpx.Client) -> pl.DataFrame:
    """
    Returns the current league table
    """

    return (pl.DataFrame(client.get("leagues-classic/737576/standings/").json()["standings"]["results"])
            .rename({"entry": "entry_id", "player_name": "manager_name"})
            .select(["entry_id", "manager_name", "entry_name", "total"])
            .with_columns(pl.col("entry_id").cast(pl.Int32))
            )


def get_player_points(client: httpx.Client, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the points scored by each player in a gameweek
    """

    return pl.json_normalize(client.get(f"event/{gameweek_id}/live/").json()["elements"]).select([
        "id",
        "stats.total_points",
        "stats.minutes",
        "stats.goals_scored",
        "stats.assists",
        "stats.clean_sheets",
        "stats.goals_conceded",
        "stats.own_goals",
        "stats.penalties_saved",
        "stats.penalties_missed",
        "stats.yellow_cards",
        "stats.red_cards",
        "stats.saves",
        "stats.bonus"
    ]).rename({"id": "player_id"})


def latest_player_activity(cache: pl.DataFrame, unique_player_points: pl.DataFrame, event_id: int) -> pl.DataFrame | None:
    """
    Returns the latest events and associated managers for players whose points have changed since the last refresh
    """

    event_time = datetime.now()

    # get players whose points have changed since last refresh
    points_diff = (unique_player_points
                   .join(cache, on="player_id", suffix="_cache")
                   .sort("team_name", "web_name", descending=True)
                   .filter(pl.col("stats.total_points") != pl.col("stats.total_points_cache")))

    activity_dfs = []

    for config in SCORING_CONFIG:
        # get rows for scoring event
        df = points_diff.filter(config["filter"])
        if not df.is_empty():
            # add event description as new column
            df = df.with_columns(event=pl.lit(config["event"]))
            # add absolute points if value is integer
            if isinstance(config["points"], int):
                df = df.with_columns(points=pl.lit(config["points"]))
            # otherwise points come from expression
            else:
                df = df.with_columns(config["points"])

            # points can be positive or negative and if not always the same type, concat will fail
            # so ensure always Int64
            df = df.with_columns(pl.col("points").cast(pl.Int64))

            activity_dfs.append(df)

    if not activity_dfs:
        return None

    activity_df = pl.concat(activity_dfs)
    # add current timestamp as event time
    activity_df = activity_df.with_columns(time=pl.lit(event_time.strftime("%H:%M")))
    # add incrementing integers as id
    activity_df = activity_df.with_columns(pl.arange(event_id, event_id+activity_df.height).alias("id"))

    return (activity_df.rename(
        {
            "web_name": "player",
            "team_name": "team",
            "position_name": "position",
            "stats.total_points": "total_points"
        })
        .select(["id", "time", "player", "team", "position", "event", "points", "total_points", "img_url"])
    )
