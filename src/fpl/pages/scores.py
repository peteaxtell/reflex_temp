import asyncio

import reflex as rx

from ..components.page_header import page_header
from ..data.api import api_client, current_gameweek_id, get_fixtures
from ..templates.template import template


class State(rx.State):

    data: list[dict] = []
    gameweek_id: int

    @rx.event(background=True)
    async def get_data(self):
        """
        Periodically get latest scores from the API
        """

        while True:
            async with self:
                with api_client() as client:

                    fixtures_df = get_fixtures(client, self.gameweek_id)

                self.data = fixtures_df.to_dicts()

            await asyncio.sleep(5)

    @rx.event()
    def set_gameweek(self):
        """
        Sets the current gameweek id
        """

        self.gameweek_id = current_gameweek_id()


def card_text(text: str | int) -> rx.Component:
    """
    Returns text component for a score card
    """

    return rx.text(text, size=rx.breakpoints(initial="1", md="3"), height="100%")


def card_row(img: str, team: str, score: int) -> rx.Component:
    """
    Returns component containing team logo, name and score in a row
    """

    return rx.flex(
        rx.box(rx.image(img, height=rx.breakpoints(initial="20px", md="35px"))),
        rx.box(card_text(team), flex_grow=1),
        rx.box(card_text(score)),
        direction="row",
        spacing="4",
        width="100%"
    )


def card(data: dict[str, any]) -> rx.Component:
    """
    Returns card containing the fixture details and score
    """

    return rx.card(
        rx.vstack(
            rx.text(data["status"], align="center", width="100%", size=rx.breakpoints(initial="1", md="3")),
            card_row(data["home_team_logo"], data["home_team_name"], data["home_team_score"]),
            card_row(data["away_team_logo"], data["away_team_name"], data["away_team_score"]),
            margin_left=rx.breakpoints(initial="7px", md="20px"),
            margin_right=rx.breakpoints(initial="7px", md="20px"),
            spacing="1",
        )
    )


def grid(mobile: bool) -> rx.Component:
    """
    Returns grid containing the fixture cards
    """

    return rx.grid(
        rx.foreach(State.data, card),
        columns=("2" if mobile else "4"),
        spacing=("2" if mobile else "4")
    )


def responsive_grid() -> rx.Component:
    """
    Returns an AG Grid with columns based on screen size
    """

    return rx.inset(
        rx.mobile_only(grid(True)),
        rx.tablet_and_desktop(grid(False)),
    )


@template(route="/live-scores", title="Live Scores", on_load=[State.set_gameweek, State.get_data])
def scores():
    """
    Returns the live scores page
    """

    return rx.flex(
        page_header("Live Scores", State.gameweek_id),
        responsive_grid(),
        direction="column",
        spacing="4",
        width="100%"
    )
