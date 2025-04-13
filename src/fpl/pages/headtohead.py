
import asyncio

import polars as pl
import reflex as rx

from ..data.api import (api_client, current_gameweek_id, get_entry_picks,
                        get_fixtures, get_player_points)
from ..templates import template

OLLIE_ENTRY_ID = 1302247
PETE_ENTRY_ID = 3722253

MIN_PLAYERS = {
    "Goalkeeper": 1,
    "Defender": 3,
    "Midfielder": 3,
    "Forward": 1
}


def swap_players(df: pl.DataFrame, unused_players: pl.DataFrame, position_in: int) -> pl.DataFrame:

    position_out = unused_players.row(0, named=True)["position"]

    return (
        df.with_columns(
            pl.when(pl.col("position") == position_in)
            .then(pl.lit(True))
            .alias("is_sub")
        )
        .with_columns(
            pl.when(pl.col("position") == position_out)
            .then(pl.lit(0))
            .when(pl.col("position") == position_in)
            .then(pl.lit(1))
            .otherwise(pl.col("multiplier"))
            .alias("multiplier")
        )
        .with_columns(
            pl.when(pl.col("position") == position_out)
            .then(pl.lit(position_in))
            .when(pl.col("position") == position_in)
            .then(pl.lit(position_out))
            .otherwise(pl.col("position"))
            .alias("position")
        )
    )


def used_minimum(df: pl.DataFrame, position: str) -> bool:

    return df.filter(pl.col("played") & (pl.col("position_name") == position)).shape[0] >= MIN_PLAYERS[position]


def unused_starters(df: pl.DataFrame, position: str) -> pl.DataFrame:
    """
    Returns players who are unused and not in the starting 11
    """

    return df.filter((pl.col("position") < 12) & (pl.col("unused")) & (pl.col("position_name") == position))


def apply_substitutions(df: pl.DataFrame) -> pl.DataFrame:

    for used_sub in df.filter(~pl.col("unused") & (pl.col("position").is_between(12, 15))).sort("position").iter_rows(named=True):

        match used_sub["position_name"]:

            case "Goalkeeper":

                # substitute goalkeeper can be swapped for unused starting goalkeeper

                unused_goalkeepers = unused_starters(df, "Goalkeeper")

                if not unused_goalkeepers.is_empty():
                    df = swap_players(df, unused_goalkeepers, used_sub["position"])

            case "Defender":

                # substitute defender can be swapped for unused starting defender

                unused_defenders = unused_starters(df, "Defender")

                if not unused_defenders.is_empty():
                    df = swap_players(
                        df, unused_defenders, used_sub["position"])
                    continue

                # substitute defender can be swapped for unused starting midfielder
                # if sufficient number of used midfielders have played

                unused_midfielders = unused_starters(df, "Midfielder")

                if (not unused_midfielders.is_empty()) & used_minimum(df, "Midfielder"):
                    df = swap_players(
                        df, unused_midfielders, used_sub["position"])
                    continue

                # substitute defender can be swapped for unused starting forward
                # if sufficient number of used forwards have played

                unused_forwards = unused_starters(df, "Forward")

                if (not unused_forwards.is_empty()) & used_minimum(df, "Forward"):
                    df = swap_players(
                        df, unused_forwards, used_sub["position"])
                    continue

            case "Midfielder":

                # substitute midfielder can be swapped for unused starting defender
                # if sufficient number of used defenders have played

                unused_defenders = unused_starters(df, "Defender")

                if (not unused_defenders.is_empty()) & used_minimum(df, "Defender"):
                    df = swap_players(
                        df, unused_defenders, used_sub["position"])
                    continue

                # substitute midfielder can be swapped for unused starting midfielder

                unused_midfielders = unused_starters(df, "Midfielder")

                if not unused_midfielders.is_empty():
                    df = swap_players(
                        df, unused_midfielders, used_sub["position"])
                    continue

                # substitute midfielder can be swapped for unused starting forward
                # if sufficient number of used forwards have played

                unused_forwards = unused_starters(df, "Forward")

                if (not unused_forwards.is_empty()) & used_minimum(df, "Forward"):
                    df = swap_players(
                        df, unused_defenders, used_sub["position"])
                    continue

            case "Forward":

                # substitute forward can be swapped for unused starting defender
                # if sufficient number of used defenders have played

                unused_defenders = unused_starters(df, "Defender")

                if (not unused_defenders.is_empty()) & used_minimum(df, "Defender"):
                    df = swap_players(
                        df, unused_defenders, used_sub["position"])
                    continue

                # substitute forward can be swapped for unused starting midfielder
                # if sufficient number of used midfielders have played

                unused_midfielders = unused_starters(df, "Midfielder")

                if (not unused_midfielders.is_empty()) & used_minimum(df, "Midfielder"):
                    df = swap_players(
                        df, unused_defenders, used_sub["position"])
                    continue

                # substitute forward can be swapped for unused starting forward

                unused_forwards = unused_starters(df, "Forward")

                if not unused_forwards.is_empty():
                    df = swap_players(
                        df, unused_forwards, used_sub["position"])
                    continue

    return df


class State(rx.State):

    ollie_data: list[dict] = []
    pete_data: list[dict] = []
    ollie_total: int = 0
    pete_total: int = 0
    gameweek_id: int

    @rx.event(background=True)
    async def get_data(self):
        """
        Periodically get latest player points from the API
        """

        from ..data.cache import PLAYERS_DF, TEAMS_DF

        while True:
            async with self:

                with api_client() as client:

                    fixtures = get_fixtures(client, self.gameweek_id)
                    home_fixtures = fixtures.rename({"home_team_id": "team_id"}).select(["team_id", "status"])
                    away_fixtures = fixtures.rename({"away_team_id": "team_id"}).select(["team_id", "status"])

                    team_fixtures = pl.concat((home_fixtures, away_fixtures)).group_by(
                        "team_id").agg((pl.col("status") != "FT").sum().alias("remaining"))

                    points_df = get_player_points(client, self.gameweek_id).join(
                        PLAYERS_DF, on="player_id").join(team_fixtures, on="team_id")

                    points_df = (
                        points_df.with_columns(
                            unused=(pl.col("stats.minutes") == 0) & (pl.col("remaining") == 0))
                        .with_columns(played=pl.col("stats.minutes") > 0)
                    )

                    ollie_players_df = get_entry_picks(client, OLLIE_ENTRY_ID, self.gameweek_id)
                    ollie_player_points = ollie_players_df.join(points_df, on="player_id")
                    ollie_player_points = ollie_player_points.with_columns(
                        unused_starter=((pl.col("position") < 12) & (pl.col("unused"))))
                    ollie_player_points = apply_substitutions(ollie_player_points)
                    ollie_player_points = ollie_player_points.filter(pl.col("position") < 12).rename(
                        {"stats.total_points": "points"}).sort("position")
                    ollie_player_points = ollie_player_points.with_columns(
                        pl.col("points").mul(pl.col("multiplier")))

                    pete_players_df = get_entry_picks(client, PETE_ENTRY_ID, self.gameweek_id)
                    pete_player_points = pete_players_df.join(points_df, on="player_id")
                    pete_player_points = pete_player_points.with_columns(
                        unused_starter=((pl.col("position") < 12) & (pl.col("unused"))))
                    pete_player_points = apply_substitutions(pete_player_points)
                    pete_player_points = pete_player_points.filter(pl.col("position") < 12).rename(
                        {"stats.total_points": "points"}).sort("position")
                    pete_player_points = pete_player_points.with_columns(
                        pl.col("points").mul(pl.col("multiplier")))

                    self.ollie_data = ollie_player_points.to_dicts()
                    self.pete_data = pete_player_points.to_dicts()

                    self.ollie_total = ollie_player_points["points"].sum()
                    self.pete_total = pete_player_points["points"].sum()

                await asyncio.sleep(5)

    @rx.event()
    def set_gameweek(self):
        """
        Sets the current gameweek id
        """

        self.gameweek_id = current_gameweek_id()


def card(data: dict[str, any]) -> rx.Component:
    """
    Returns card containing the point updates for a player
    """

    return rx.hstack(
        rx.image(data["img_url"], height="37px"),
        rx.hstack(
            rx.text(data["web_name"], size="1"),
            rx.cond(
                data["is_captain"],
                rx.badge("C", size="1", color_scheme="green"),
            ),
            rx.cond(
                data["is_sub"],
                rx.badge(rx.icon("refresh-ccw", size=14), color_scheme="blue"),
            ),
            flex="1",
            spacing="1",
        ),
        rx.text(data["points"], size="1",),
        align="center",
        width="100%"
    )


def cards(data: list[dict]) -> rx.Component:
    """
    Returns cards showing player points
    """

    return rx.flex(
        rx.foreach(data, card),
        direction="column",
        spacing="2",
        padding="0px 7px",
        width="100%",
    )


def player_summary(player: str, points: int, data: list[dict]) -> rx.Component:
    """
    Returns a column containing player photo, points and player points
    """

    return rx.flex(
        rx.image(f"/{player}.jpeg", height="60px", width="60px", border_radius="50%"),
        rx.badge(points, size="2", color_scheme="green"),
        rx.divider(size="1", width="80%"),
        cards(data),
        direction="column",
        spacing="4",
        align="center",
        width="48%"
    )


@template(route="/", title="Head to Head", on_load=[State.set_gameweek, State.get_data])
def head_to_head():
    """
    Returns the head to head competition
    """

    return rx.flex(
        player_summary("ollie", State.ollie_total, State.ollie_data),
        rx.divider(orientation="vertical", size="2", height="calc(100dvh - 130px)"),
        player_summary("pete", State.pete_total, State.pete_data),
        direction="row",
        spacing="4",
        width="100%"
    )
