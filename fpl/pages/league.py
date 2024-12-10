import asyncio
from concurrent.futures import ThreadPoolExecutor

import polars as pl
import reflex as rx
from reflex_ag_grid.ag_grid import ColumnDef, ag_grid

from ..data.api import (api_client, get_entry_points, get_gameweek,
                        get_league_picks, get_league_table, get_player_points)
from ..templates.template import template


class State(rx.State):

    data: list[dict] = [{}]
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

                    # get entries in the league
                    league_df = get_league_table(client)

                    # get players picked for each entry in current gameweek
                    picked_players_df = get_league_picks(client, self.gameweek_id, league_df)

                    # get captain for each entry
                    captains_df = (
                        picked_players_df.filter(pl.col("is_captain"))
                        .select(("entry_id", "web_name"))
                        .rename({"web_name": "captain"})
                    )

                    # get points from previous gameweek for each entry
                    with ThreadPoolExecutor() as executor:
                        prev_gw_points_df = list(executor.map(lambda entry_id: get_entry_points(
                            client, entry_id, self.gameweek_id-1), league_df["entry_id"].to_list()))

                    prev_gw_points_df = (
                        pl.concat(prev_gw_points_df)
                        .rename({"total_points": "previous_total_points"})
                    )

                    # get live points for each entry
                    live_points_df = (
                        picked_players_df
                        .join(get_player_points(client, self.gameweek_id), on="player_id")
                        .with_columns(pl.col("stats.total_points").mul(pl.col("multiplier")))
                        .group_by(["entry_id", "manager_name"])
                        .agg(pl.col("stats.total_points").sum().alias("live_points"))
                    )

                # join previous week and live points add total points column for each entry
                df = (
                    prev_gw_points_df.join(live_points_df, on="entry_id")
                    .join(captains_df, on="entry_id")
                    .with_columns(pl.col("previous_total_points").add(pl.col("live_points")).alias("total_points"))
                    .sort(["total_points", "manager_name"], descending=True)
                )

                self.data = df.to_dicts()

            await asyncio.sleep(5)

    @rx.event()
    def set_gameweek(self):
        gw = get_gameweek()
        self.gameweek_id = gw["gameweek_id"]
        self.gameweek_deadline = gw["deadline_time"].strftime("%d %b %H:%M")


def col_defs(mobile: bool) -> list[ColumnDef]:
    """
    Returns column defs for AG Grid tailored to window size
    """

    cols = [
        ColumnDef(
            field="entry_id",
            hide=True
        ),
        ColumnDef(
            field="manager_name",
            header_name="Player"
        ),
        ColumnDef(
            field="captain",
            header_name="Captain",
            hide=mobile
        ),
        ColumnDef(
            field="live_points",
            header_name="Week"
        ),
        ColumnDef(
            field="total_points",
            header_name="Total"
        )
    ]

    if mobile:
        cols[3].max_width = 100
        cols[4].max_width = 100

    return cols


def grid(mobile: bool):
    """
    Returns a grid
    """

    return ag_grid(
        id="ag-league",
        column_defs=col_defs(mobile),
        row_data=State.data,
        auto_size_strategy={"type": "SizeColumnsToFitGridStrategy"},
        theme="quartz",
        width="100%",
        height="calc(100dvh - 240px)",
        overflow="auto"
    )


@template(route="/", title="League Table", on_load=[State.set_gameweek, State.get_data])
def league():
    return rx.flex(
        rx.heading("League Table"),
        rx.text(f"Gameweek {State.gameweek_id}", size="2"),
        rx.divider(width="100%"),
        rx.mobile_only(grid(True)),
        rx.tablet_and_desktop(grid(False)),
        spacing="4",
        direction="column",
        width="100%"
    )
