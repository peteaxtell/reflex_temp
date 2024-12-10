import asyncio

import polars as pl
import reflex as rx
from reflex_ag_grid.ag_grid import ColumnDef, ag_grid

from ..data.api import (api_client, get_gameweek, get_league_picks,
                        get_league_table, get_player_points,
                        latest_player_activity)
from ..templates.template import template


class State(rx.State):

    live_update_data: list[dict] = []
    player_points_cache: list[dict] = []
    gameweek_id: int
    gameweek_deadline: str

    @rx.event(background=True)
    async def get_data(self):
        """
        Get latest data from the API
        """

        while True:
            async with self:
                with api_client() as client:

                    league_df = get_league_table(client)
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

            await asyncio.sleep(500)

    @rx.event()
    def set_gameweek(self):
        gw = get_gameweek()
        self.gameweek_id = gw["gameweek_id"]
        self.gameweek_deadline = gw["deadline_time"].strftime("%d %b %H:%M")


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


def grid(mobile: bool):
    """
    Returns a grid
    """

    return ag_grid(
        id="ag-live",
        column_defs=col_defs(mobile),
        row_data=State.live_update_data,
        auto_size_strategy={"type": "SizeColumnsToFitGridStrategy"},
        theme="quartz",
        width="100%",
        height="calc(100dvh - 240px)",
        overflow="auto",
        style={"--ag-row-height": "75px !important;"}
    )


@template(route="/live-updates", title="Live Updates", on_load=[State.set_gameweek, State.get_data])
def live():
    return rx.flex(
        rx.heading("Live Updates"),
        rx.text(f"Gameweek {State.gameweek_id}", size="2"),
        rx.divider(width="100%"),
        rx.mobile_only(grid(True)),
        rx.tablet_and_desktop(grid(False)),
        spacing="4",
        direction="column",
        width="100%"
    )
