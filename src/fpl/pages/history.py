from concurrent.futures import ThreadPoolExecutor

import polars as pl
import reflex as rx

from ..components.league_selector import LeagueSelectState
from ..components.page_header import page_header
from ..data.api import (api_client, current_gameweek_id,
                        get_entry_points_history, get_league_table)
from ..templates.template import template


class State(rx.State):

    data: list[dict] = []
    entry_ids: list[int] = []
    gameweek_id: int

    @rx.event()
    async def get_data(self):
        """
        Get points history for league from API
        """

        league_selector = await self.get_state(LeagueSelectState)

        if league_selector.selected_league:

            with api_client() as client:

                # get entries in the league
                league_df = get_league_table(client, league_selector.selected_league.id)

                self.entry_ids = league_df["entry_id"].unique().to_list()

                # get points from previous gameweek for each entry
                with ThreadPoolExecutor() as executor:
                    points_history_df = list(executor.map(lambda entry_id: get_entry_points_history(
                        client, entry_id), league_df["entry_id"].to_list()))

            points_history_df = (pl.concat(points_history_df)).sort("gameweek_id").group_by("gameweek_id")

            data = []

            # get points per gameweek for each entry in format for chart
            for gameweek_id, entry_points in points_history_df:
                gameweek_points = {"gameweek_id": gameweek_id}
                gameweek_points.update(
                    dict(zip(entry_points["entry_id"].to_list(), entry_points["total_points"].to_list())))
                data.append(gameweek_points)

        self.data = data

    @rx.event()
    def set_gameweek(self):
        """
        Sets the current gameweek id
        """

        self.gameweek_id = current_gameweek_id()


@template(route="/history", title="League History", on_load=[State.set_gameweek, State.get_data])
def history():
    """
    Returns the league history page
    """

    return rx.flex(
        page_header("Leauge History", State.gameweek_id),
        rx.recharts.line_chart(
            rx.foreach(
                State.entry_ids,
                lambda x: rx.recharts.line(data_key=x)
            ),
            rx.recharts.x_axis(data_key="gameweek_id"),
            rx.recharts.y_axis(),
            rx.recharts.legend(),
            data=State.data,
            width="100%",
            height=500
        ),
        direction="column",
        spacing="4",
        width="100%"
    )
