import asyncio

import polars as pl
import reflex as rx

from ..data.api import (api_client, current_gameweek_id, get_entry_picks,
                        get_player_points)
from ..templates.template import template

OLLIE_ENTRY_ID = 1302247
PETE_ENTRY_ID = 3722253


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

        from ..data.cache import PLAYERS_DF

        while True:
            async with self:

                with api_client() as client:

                    points_df = get_player_points(client, self.gameweek_id)

                    ollie_players_df = get_entry_picks(client, OLLIE_ENTRY_ID, self.gameweek_id)
                    pete_players_df = get_entry_picks(client, PETE_ENTRY_ID, self.gameweek_id)

                    ollie_player_points = (ollie_players_df
                                           .join(points_df, on="player_id")
                                           )

                    pete_player_points = (pete_players_df
                                          .join(points_df, on="player_id")
                                          )

                ollie_player_points = ollie_player_points.join(
                    PLAYERS_DF, on="player_id").filter(pl.col("position") < 12).rename({"stats.total_points": "points"}).sort("position")

                pete_player_points = pete_player_points.join(
                    PLAYERS_DF, on="player_id").filter(pl.col("position") < 12).rename({"stats.total_points": "points"}).sort("position")

                ollie_player_points = ollie_player_points.with_columns(pl.col("points").mul(pl.col("multiplier")))
                pete_player_points = pete_player_points.with_columns(pl.col("points").mul(pl.col("multiplier")))

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
        spacing="4",
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
        spacing="5",
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
