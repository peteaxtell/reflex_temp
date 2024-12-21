from concurrent.futures import ThreadPoolExecutor
from itertools import groupby

import polars as pl
import reflex as rx

from ..components.callout import callout
from ..components.league_selector import LeagueSelectState
from ..components.page_header import page_header
from ..data.api import (api_client, current_gameweek_id, get_league_table,
                        get_transfers)
from ..templates.template import template


class State(rx.State):

    data: dict[str, list[dict]] = {}
    gameweek_id: int

    @rx.event(background=True)
    async def get_data(self):
        """
        Get latest gameweek transfers from the API
        """
        async with self:

            league_selector = await self.get_state(LeagueSelectState)

            if league_selector.selected_league:

                with api_client() as client:

                    # get entries in the league
                    league_df = get_league_table(client, league_selector.selected_league.id)

                    # get trasnfers for current gameweek for each entry
                    with ThreadPoolExecutor() as executor:
                        transfers_df = list(executor.map(lambda entry_id: get_transfers(
                            client, entry_id, self.gameweek_id, league_df), league_df["entry_id"].to_list()))

                    transfers_df = (pl.concat([df for df in transfers_df if df is not None]))

                for manager, transfers in groupby(transfers_df.to_dicts(), lambda x: x["manager_name"]):
                    self.data[manager] = list(transfers)

    @rx.event()
    def set_gameweek(self):
        """
        Sets the current gameweek id
        """

        self.gameweek_id = current_gameweek_id()


def card_column(direction_icon: str, player_img: str, player_name: str) -> rx.Component:
    """
    Returns a column within a card containing the direction icon, player image and name
    """

    return rx.flex(
        rx.box(rx.image(direction_icon, height="30px", width="30px")),
        rx.vstack(
            rx.box(rx.image(player_img, height="60px", width="60px")),
            rx.text(player_name, size=rx.breakpoints(initial="1", md="2")),
            align="center",
        ),
        align="center",
        spacing="2",
        width="50%"
    )


def card_row(img_url_out: str, name_out: str, img_url_in: str, name_in: str) -> rx.Component:
    """
    Returns component containing transfer direction and player in a row
    """

    return rx.flex(
        card_column("/icons/out.png", img_url_out, name_out),
        card_column("/icons/in.png", img_url_in, name_in),
        direction="row",
        spacing="4",
        width="100%"
    )


def card(data: tuple[str, dict[str, any]]) -> rx.Component:
    """
    Returns card containing the managers gameweek transfers
    """

    return rx.card(
        rx.vstack(
            rx.text(data[0], align="center", width="100%", size=rx.breakpoints(initial="1", md="3")),
            rx.foreach(
                data[1],
                lambda transfer: card_row(
                    transfer["img_url_out"],
                    transfer["web_name_out"],
                    transfer["img_url_in"],
                    transfer["web_name_in"]
                )
            ),
            margin_left=rx.breakpoints(initial="7px", md="20px"),
            margin_right=rx.breakpoints(initial="7px", md="20px"),
            spacing="1",
        )
    )


def grid(mobile: bool) -> rx.Component:
    """
    Returns grid containing the gameweek transfers
    """

    return rx.grid(
        rx.foreach(State.data.items(), card),
        columns=("2" if mobile else "4"),
        spacing=("2" if mobile else "4")
    )


def responsive_grid() -> rx.Component:
    """
    Returns an grid with columns based on screen size
    """

    return rx.inset(
        rx.mobile_only(grid(True)),
        rx.tablet_and_desktop(grid(False)),
    )


@ template(route="/transfers", title="League Table", on_load=[State.set_gameweek, State.get_data])
def transfers():
    """
    Returns the latest gameweek transfers
    """

    return rx.flex(
        page_header("Tranfers", State.gameweek_id),
        rx.cond(
            ~LeagueSelectState.selected_league,
            callout("Select a league to view table"),
            responsive_grid()
        ),
        direction="column",
        spacing="4",
        width="100%"
    )
