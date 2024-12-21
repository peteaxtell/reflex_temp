import json

import polars as pl

GAMEWEEKS_DF = None
PLAYERS_DF = None
TEAMS_DF = None


def _cache_gameweeks(gameweeks_data: dict[str, any]):
    """
    Cache static gameweek data
    """

    global GAMEWEEKS_DF

    col_map = {
        "id": "gameweek_id"
    }

    return_fields = (
        "gameweek_id",
        "deadline_time"
    )

    GAMEWEEKS_DF = (
        pl.DataFrame(gameweeks_data)
        .rename(col_map)
        .with_columns(pl.col("deadline_time").str.strptime(pl.Datetime, format="%+"))
        .select(return_fields)
    )


def _cache_players(players_data: dict[str, any], positions_data: dict[str, any]):
    """
    Cache static player data
    """

    global PLAYERS_DF

    players_col_map = {
        "id": "player_id",
        "team": "team_id",
        "element_type": "position_id",
        "photo": "img_filename"
    }

    positions_col_map = {
        "id": "position_id",
        "singular_name": "position_name"
    }

    return_fields = (
        "player_id",
        "web_name",
        "team_id",
        "team_name",
        "position_name",
        "img_url"
    )

    # api returns jpg but the hosted images are png
    img_to_png = pl.col("img_filename").str.replace(".jpg", ".png")

    img_url = (
        pl.concat_str(
            pl.lit(
                "https://resources.premierleague.com/premierleague/photos/players/250x250/p"),
            pl.col("img_filename")
        )
        .alias("img_url")
    )

    players_df = (
        pl.json_normalize(players_data)
        .rename(players_col_map)
        .with_columns(img_to_png)
        .with_columns(img_url)
    )

    positions_df = (
        pl.json_normalize(positions_data)
        .rename(positions_col_map)
    )

    PLAYERS_DF = (
        players_df.join(TEAMS_DF, on="team_id", how="left")
        .join(positions_df, on="position_id")
        .select(return_fields)
    )


def _cache_teams(teams_data: dict[str, any]):
    """
    Cache static team data
    """

    global TEAMS_DF

    col_map = {
        "id": "team_id",
        "name": "team_name"
    }

    return_fields = (
        "team_id",
        "team_name",
        "logo"
    )

    logo = (
        pl.concat_str(
            (
                pl.lit("/logos/"),
                pl.col("team_name").str.to_lowercase().str.replace(" ", "_"),
                pl.lit(".png")
            )
        )
        .alias("logo")
    )

    TEAMS_DF = (
        pl.json_normalize(teams_data)
        .rename(col_map)
        .with_columns(logo)
        .select(return_fields)
    )


def cache_data():
    """
    Returns static team and player metadata
    """

    from .api import api_client

    with api_client() as client:
        # bootstrap_data = client.get("bootstrap-static/").json()
        with open(r"C:\Users\pda\Python\code\reflex_temp\src\fpl\data\__mock\bootstrap.json", "r") as f:
            bootstrap_data = json.loads(f.read())

    _cache_teams(bootstrap_data["teams"])
    _cache_players(bootstrap_data["elements"], bootstrap_data["element_types"])
    _cache_gameweeks(bootstrap_data["events"])
