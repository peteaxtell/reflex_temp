from concurrent.futures import ThreadPoolExecutor

import polars as pl
import reflex as rx
from reflex_ag_grid.ag_grid import ColumnDef, ag_grid

from ..components.callout import callout
from ..components.league_selector import LeagueSelectState
from ..components.page_header import page_header
from ..data.api import (api_client, current_gameweek_id, get_league_table,
                        get_transfers)
from ..templates.template import template


class State(rx.State):

    data: list[dict] = []
    gameweek_id: int

    @rx.event(background=True)
    async def get_data(self):
        """
        Get latest gameweek transfers from the API
        """

        while True:
            async with self:

                league_selector = await self.get_state(LeagueSelectState)

                if league_selector.selected_league:

                    with api_client() as client:

                        # get entries in the league
                        league_df = get_league_table(client, league_selector.selected_league.id)

                        # get trasnfers for current gameweek for each entry
                        with ThreadPoolExecutor() as executor:
                            transfers_df = list(executor.map(lambda entry_id: get_transfers(
                                client, entry_id, self.gameweek_id), league_df["entry_id"].to_list()))

                        transfers_df = (pl.concat(transfers_df))

                    self.data = transfers_df.to_dicts()

    @rx.event()
    def set_gameweek(self):
        """
        Sets the current gameweek id
        """

        self.gameweek_id = current_gameweek_id()


def col_defs() -> list[ColumnDef]:
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
            header_name="Manager"
        ),
        ColumnDef(
            field="player_in",
            header_name="Transfer In"
        ),
        ColumnDef(
            field="player_out",
            header_name="Transfer Out"
        )
    ]

    return cols


def grid() -> rx.Component:
    """
    Returns an AG Grid
    """

    return ag_grid(
        id="ag-transfers",
        auto_size_strategy={"type": "SizeColumnsToFitGridStrategy"},
        column_defs=col_defs(),
        height="calc(100dvh - 240px)",
        overflow="auto",
        row_data=State.data,
        theme="quartz",
        width="100%",
    )


@template(route="/transfers", title="League Table", on_load=[State.set_gameweek, State.get_data])
def transfers():
    """
    Returns the latest gameweek transfers
    """

    return rx.flex(
        page_header("Tranfers", State.gameweek_id),
        rx.cond(
            ~LeagueSelectState.selected_league,
            callout("Select a league to view table"),
            grid()
        ),
        direction="column",
        spacing="4",
        width="100%"
    )
