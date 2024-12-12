from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import httpx
import polars as pl
import pytz

from ..exceptions.fpl_api_exception import FplApiException
from .config import *


def api_client() -> httpx.Client:
    """
    Returns a client for connecting to the FPL API
    """

    return httpx.Client(
        base_url="https://fantasy.premierleague.com/api",
        event_hooks={"response": [lambda x: x.raise_for_status()]}
    )


def current_gameweek_id() -> int:
    """
    Returns the current gameweek id
    """

    from .cache import GAMEWEEKS_DF

    return (
        GAMEWEEKS_DF.filter(pl.col("deadline_time") <= datetime.now(pytz.UTC))
        .sort("deadline_time", descending=True)
        .row(0)[0]
    )


def get_entry_history(client: httpx.Client, entry_id: int) -> pl.DataFrame:
    """
    Returns the points by week for the entry
    """

    col_map = {"event": "gameweek_id"}

    return_fields = (
        "gameweek_id",
        "entry_id",
        "total_points"
    )

    try:
        api_data = client.get(f"entry/{entry_id}/history/").json()["current"]

        return (
            pl.DataFrame(api_data)
            .with_columns(entry_id=entry_id)
            .rename(col_map)
            .select(return_fields)
        )

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise FplApiException(f"No points history found for entry {entry_id}")
        raise FplApiException(f"Error getting points history for entry {entry_id} from Fantasy Premier League")
    except Exception:
        raise Exception(f"Error getting points history for entry {entry_id}")


def get_entry_picks(client: httpx.Client, entry_id: int, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the gameweek picks for an entry
    """

    col_map = {
        "element": "player_id"
    }

    return_cols = (
        "entry_id",
        "player_id",
        "position",
        "multiplier",
        "is_captain"
    )

    try:
        api_data = client.get(f"entry/{entry_id}/event/{gameweek_id}/picks/").json()["picks"]

        return (
            pl.DataFrame(api_data)
            .with_columns(entry_id=entry_id)
            .rename(col_map)
            .select(return_cols)
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise FplApiException(f"No selected players found for entry {entry_id}")
        raise FplApiException(f"Error getting selected players for entry {entry_id} from Fantasy Premier League")
    except Exception:
        raise Exception(f"Error getting selected players for entry {entry_id}")


def get_entry_points(client: httpx.Client, entry_id: int, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the total points for an entry at the end of a gameweek
    """

    return_fields = (
        "entry_id",
        "total_points"
    )

    try:
        api_data = client.get(f"entry/{entry_id}/event/{gameweek_id}/picks/").json()["entry_history"]

        return (
            pl.DataFrame(api_data)
            .with_columns(entry_id=entry_id).cast(pl.Int32)
            .select(return_fields)
        )
    except httpx.HTTPStatusError:
        raise FplApiException(f"""Error getting player points for entry {entry_id} in gameweek
                              {gameweek_id} from Fantasy Premier League""")
    except Exception:
        raise Exception(f"Error getting player points for entry {entry_id} in gameweek {gameweek_id}")


def get_fixtures(client: httpx.Client, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the fixtures and scores for the gameweek
    """

    from .cache import TEAMS_DF

    col_map = {
        "team_h": "home_team_id",
        "team_h_score": "home_team_score",
        "team_a": "away_team_id",
        "team_a_score": "away_team_score",
    }

    return_fields = (
        "id",
        "kickoff_time",
        "status",
        "home_team_name",
        "home_team_score",
        "home_team_logo",
        "away_team_name",
        "away_team_score",
        "away_team_logo"
    )

    # convert to date for sorting
    kickoff_time = pl.col("kickoff_time").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%SZ").alias("kickoff_time")

    # status column will contain elapsed time of scheduled kick-off e.g. 59' / FT / Sat 12 Sep 15:00
    status = (
        pl.when(pl.col("finished_provisional") == True)
        .then(pl.lit("FT"))
        .otherwise(
            pl.when(pl.col("kickoff_time") <= datetime.now())
            .then(pl.concat_str(
                pl.col("minutes"),
                pl.lit("'")
            ))
            .otherwise(pl.col("kickoff_time").dt.strftime("%a %d %b %H:%M"))
        )
        .alias("status")
    )

    try:
        api_data = client.get("fixtures/").json()

        df = pl.DataFrame(api_data).filter(pl.col("event") == gameweek_id)

        if df.is_empty():
            return pl.DataFrame()

        return (
            df.with_columns(kickoff_time)
            .with_columns(status)
            .rename(col_map)
            .join(TEAMS_DF, left_on="away_team_id", right_on="team_id")
            .rename({"team_name": "away_team_name", "logo": "away_team_logo"})
            .join(TEAMS_DF, left_on="home_team_id", right_on="team_id")
            .rename({"team_name": "home_team_name", "logo": "home_team_logo"})
            .sort(pl.col("kickoff_time"))
            .select(return_fields)
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise FplApiException(f"No fixtures found for gameweek {gameweek_id}")
        raise FplApiException(f"Error getting fixtures for gameweek {gameweek_id} from Fantasy Premier League")
    except Exception:
        raise Exception(f"Error getting fixtures for gameweek {gameweek_id}")


def get_league_picks(client: httpx.Client, gameweek_id: int, league_df: pl.DataFrame) -> pl.DataFrame:
    """
    Returns the gameweek picks for all teams in the league
    """

    from .cache import PLAYERS_DF

    return_fields = (
        "entry_id",
        "manager_name",
        "team_name",
        "player_id",
        "web_name",
        "position_name",
        "position",
        "is_captain",
        "multiplier",
        "img_url"
    )

    try:
        # get picks for each entry in parallel
        with ThreadPoolExecutor() as executor:
            picks = list(executor.map(lambda entry_id: get_entry_picks(
                client, entry_id, gameweek_id), league_df["entry_id"].to_list()))

        return (
            pl.concat(picks)
            .join(PLAYERS_DF, on="player_id")
            .join(league_df, on="entry_id")
            .filter(pl.col("position") < 12)
            .select(return_fields)
        )
    except Exception:
        raise Exception(f"Error getting selected players in league for gameweek {gameweek_id}")


def get_league_table(client: httpx.Client, league_id: int) -> pl.DataFrame:
    """
    Returns the current league table
    """

    col_map = {
        "entry": "entry_id",
        "player_name": "manager_name",
    }

    return_fields = (
        "entry_id",
        "manager_name",
        "entry_name",
        "total"
    )

    try:
        api_data = client.get(f"leagues-classic/{league_id}/standings/").json()["standings"]["results"]

        return (
            pl.DataFrame(api_data)
            .rename(col_map)
            .with_columns(pl.col("entry_id").cast(pl.Int32))
            .select(return_fields)
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise FplApiException(f"No league found with id {league_id}")
        raise FplApiException(f"Error getting table for league {league_id} from Fantasy Premier League")
    except Exception:
        raise Exception(f"Error getting table for league {league_id}")


def get_player_points(client: httpx.Client, gameweek_id: int) -> pl.DataFrame:
    """
    Returns the points scored by each player in a gameweek
    """

    col_map = {
        "id": "player_id"
    }

    return_fields = (
        "id",
        "stats.assists",
        "stats.bonus",
        "stats.clean_sheets",
        "stats.goals_conceded",
        "stats.goals_scored",
        "stats.minutes",
        "stats.own_goals",
        "stats.penalties_missed",
        "stats.penalties_saved",
        "stats.red_cards",
        "stats.saves",
        "stats.total_points",
        "stats.yellow_cards",
    )

    try:
        api_data = client.get(f"event/{gameweek_id}/live/").json()["elements"]

        return (
            pl.json_normalize(api_data)
            .select(return_fields)
            .rename(col_map)
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise FplApiException(f"No live points found for gameweek {gameweek_id}")
        raise FplApiException(f"Error getting live points for gameweek {gameweek_id} from Fantasy Premier League")
    except Exception:
        raise Exception(f"Error getting live points for gameweek {gameweek_id}")


def latest_player_activity(cache: pl.DataFrame, unique_player_points: pl.DataFrame, event_id: int) -> pl.DataFrame | None:
    """
    Returns the latest events and associated managers for players whose points have changed since the last refresh
    """

    col_map = {
        "position_name": "position",
        "stats.total_points": "total_points",
        "team_name": "team",
        "web_name": "player",
    }

    return_fields = (
        "id",
        "event",
        "img_url"
        "player",
        "points",
        "position",
        "team",
        "time",
        "total_points",
    )

    try:
        event_time = datetime.now()

        # get players whose points have changed since last refresh
        points_diff = (
            unique_player_points
            .join(cache, on="player_id", suffix="_cache")
            .sort("team_name", "web_name", descending=True)
            .filter(pl.col("stats.total_points") != pl.col("stats.total_points_cache"))
        )

        activity_dfs: list[pl.DataFrame] = []

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

        return (
            activity_df
            .rename(col_map)
            .select(return_fields)
        )
    except Exception:
        raise Exception("Error calculating latest player points updates")
