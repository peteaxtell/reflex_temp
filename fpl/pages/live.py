import asyncio

import polars as pl
import reflex as rx
from reflex_ag_grid.ag_grid import ColumnDef, ag_grid

from ..components.league_picker import LeagueSelectState
from ..components.page_header import page_header
from ..data.api import (api_client, current_gameweek_id, get_league_picks,
                        get_league_table, get_player_points,
                        latest_player_activity)
from ..settings import settings
from ..templates.template import template


class State(rx.State):

    gameweek_id: int
    live_update_data: list[dict] = []
    player_points_cache: list[dict] = []

    @rx.event(background=True)
    async def get_data(self):
        """
        Periodically get latest point scoring events from the API
        """

        while True:
            async with self:

                league_selector = await self.get_state(LeagueSelectState)

                if league_selector.selected_league:
                    with api_client() as client:

                        league_df = get_league_table(client, league_selector.selected_league.id)
                        points_df = get_player_points(client, self.gameweek_id)
                        picked_players_df = get_league_picks(client, self.gameweek_id, league_df)

                        # points for uniquely selected players for the gameweek
                        live_player_points_df = (picked_players_df["player_id", "web_name", "position_name", "team_name", "img_url"]
                                                 .unique()
                                                 .join(points_df, on="player_id")
                                                 )

                        # can only work out new points if already have previous points in cache after first run
                        if self.player_points_cache:

                            latest_activity_df = latest_player_activity(pl.DataFrame(
                                self.player_points_cache.copy()), live_player_points_df, len(self.live_update_data))

                            if latest_activity_df is not None:
                                self.live_update_data = sorted(
                                    self.live_update_data + latest_activity_df.to_dicts(), key=lambda x: x["id"], reverse=True)

                        self.player_points_cache = live_player_points_df.to_dicts()

            await asyncio.sleep(settings.refresh_interval_secs)

    @rx.event()
    def set_gameweek(self):
        """
        Sets the current gameweek id
        """

        self.gameweek_id = current_gameweek_id()


badge = rx.vars.function.ArgsFunctionOperation.create(
    ("params",),
    rx.html(
        rx.Var("params.value"),
        class_name="badge_green"
    ),
).to(dict)

player = rx.vars.function.ArgsFunctionOperation.create(
    ("params",),
    rx.flex(
        rx.image(class_name="player_pill_img", src=rx.Var("params.data.img_url", _var_type=str), margin_bottom=5),
        rx.Var("params.value", _var_type=str),
        class_name="player_pill_ag",
        direction="column"
    ),
).to(dict)


def col_defs(mobile: bool) -> list[ColumnDef]:
    """
    Returns column defs for AG Grid tailored to window size
    """

    cols = [
        ColumnDef(
            field="id",
            hide=True
        ),
        ColumnDef(
            field="time",
            header_name="Time",
        ),
        ColumnDef(
            field="player",
            header_name="Player",
            cell_renderer=player
        ),
        ColumnDef(
            field="event",
            header_name="Event",
            cell_renderer=badge
        ),
        ColumnDef(
            field="total_points",
            header_name="Total",
        )
    ]

    if mobile:
        cols[1].max_width = 100
        cols[2].max_width = 100
        cols[4].max_width = 85

    return cols


def grid(mobile: bool) -> rx.Component:
    """
    Returns an AG Grid
    """

    return ag_grid(
        id="ag-live",
        auto_size_strategy={"type": "SizeColumnsToFitGridStrategy"},
        column_defs=col_defs(mobile),
        height="calc(100dvh - 240px)",
        overflow="auto",
        row_data=State.live_update_data,
        style={"--ag-row-height": "75px !important;"},
        theme="quartz",
        width="100%",
    )


def responsive_grid() -> rx.Component:
    """
    Returns an AG Grid with columns based on screen size
    """

    return rx.inset(
        rx.mobile_only(grid(True)),
        rx.tablet_and_desktop(grid(False)),
    )


def callout(text: str) -> rx.Component:
    """
    Returns a callout
    """

    return rx.callout(
        text,
        icon="info",
        color_scheme="blue",
    )


@template(route="/live-updates", title="Live Updates", on_load=[State.set_gameweek, State.get_data])
def live():
    """
    Returns the live points updates page
    """

    return rx.flex(
        page_header("Live Updates", State.gameweek_id),
        rx.cond(
            ~LeagueSelectState.selected_league,
            callout("Select a league to view live updates"),
            responsive_grid()
        ),
        direction="column",
        spacing="4",
        width="100%"
    )
