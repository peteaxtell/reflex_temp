import polars as pl

GAMEWEEKS_DF = None
PLAYERS_DF = None
TEAMS_DF = None


def cache_data():
    """
    Returns static team and player metadata
    """

    from .api import api_client

    global GAMEWEEKS_DF
    global PLAYERS_DF
    global TEAMS_DF

    with api_client() as client:
        bootstrap_data = client.get("bootstrap-static/").json()

        players_df = (
            pl.json_normalize(bootstrap_data["elements"])
            .select(["id", "web_name", "team", "element_type", "photo"])
            .rename({"id": "player_id", "team": "team_id", "element_type": "position_id", "photo": "img_filename"})
            .with_columns(pl.col("img_filename").str.replace(".jpg", ".png"))
            .with_columns(pl.concat_str(pl.lit("https://resources.premierleague.com/premierleague/photos/players/250x250/p"), pl.col("img_filename")).alias("img_url"))
        )

        positions_df = (
            pl.json_normalize(bootstrap_data["element_types"])
            .select(["id", "singular_name"])
            .rename({"id": "position_id", "singular_name": "position_name"})
        )

        TEAMS_DF = (
            pl.json_normalize(bootstrap_data["teams"])
            .select(["id", "name"])
            .rename({"id": "team_id", "name": "team_name"})
            .with_columns(
                pl.concat_str(
                    (
                        pl.lit("/logos/"),
                        pl.col("team_name").str.to_lowercase().str.replace(" ", "_"),
                        pl.lit(".png")
                    )
                ).alias("logo"))
        )

        PLAYERS_DF = players_df.join(TEAMS_DF, on="team_id", how="left").join(positions_df, on="position_id")

        GAMEWEEKS_DF = (
            pl.DataFrame(bootstrap_data["events"])
            .rename({"id": "gameweek_id"})
            .select(["gameweek_id", "deadline_time", "is_current"])
        )

        GAMEWEEKS_DF = GAMEWEEKS_DF.with_columns(pl.col("deadline_time").str.strptime(pl.Datetime, format="%+"))
