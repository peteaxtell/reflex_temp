import asyncio

import reflex as rx
from reflex_ag_grid.ag_grid import ColumnDef

from ..data.api import api_client, get_fixtures, get_gameweek
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

                    fixtures_df = get_fixtures(client, self.gameweek_id)

                self.data = fixtures_df.to_dicts()

            await asyncio.sleep(5)

    @rx.event()
    def set_gameweek(self):
        gw = get_gameweek()
        self.gameweek_id = gw["gameweek_id"]
        self.gameweek_deadline = gw["deadline_time"].strftime("%d %b %H:%M")


badge = rx.vars.function.ArgsFunctionOperation.create(
    ("params",),
    rx.flex(
        rx.image(class_name="team_pill_img", src=rx.Var("params.data.home_team_logo", _var_type=str), margin_right=8),
        rx.Var("params.value", _var_type=str),
        class_name="team_pill_ag",
        direction="row"
    ),
).to(dict)


def col_defs(mobile: bool) -> list[ColumnDef]:
    """
    Returns column defs for AG Grid tailored to window size
    """

    cols = [
        ColumnDef(
            field="kickoff_time_d",
            header=None,
            hide=True,
            sort="asc"
        ),
        ColumnDef(
            field="kickoff_time",
            hide=mobile,
            header_name=""
        ),
        ColumnDef(
            field="minutes",
            header_name=""
        ),
        ColumnDef(
            field="home_team_name",
            cell_renderer=badge,
            header_name=""
        ),
        ColumnDef(
            field="home_team_score",
            header_name=""
        ),
        ColumnDef(
            field="away_team_score",
            header_name=""
        ),
        ColumnDef(
            field="away_team_name",
            cell_renderer=badge,
            header_name=""
        ),
    ]

    if mobile:
        cols[2].max_width = 75
        cols[4].max_width = 67
        cols[5].max_width = 67

    return cols


# def grid(mobile: bool):
#     """
#     Returns a grid
#     """

#     return ag_grid(
#         id="ag-scores",
#         column_defs=col_defs(mobile),
#         row_data=State.data,
#         auto_size_strategy={"type": "SizeColumnsToFitGridStrategy"},
#         theme="quartz",
#         width="100%",
#         height="calc(100dvh - 240px)",
#         overflow="auto",
#         style={"--ag-row-height": "50px !important;"}
#     )


def card_text(text: str | int):
    return rx.text(text, size=rx.breakpoints(initial="1", md="3"), height="100%")


def card_row(img: str, team: str, score: int):

    return rx.flex(
        rx.box(rx.image(img, height=rx.breakpoints(initial="20px", md="35px"))),
        rx.box(card_text(team), flex_grow=1),
        rx.box(card_text(score)),
        direction="row",
        spacing="4",
        width="100%"
    )


def card(data: dict[str, any]):

    return rx.card(
        rx.vstack(
            rx.text(data["time"], align="center", width="100%", size=rx.breakpoints(initial="1", md="3")),
            card_row(data["home_team_logo"], data["home_team_name"], data["home_team_score"]),
            card_row(data["away_team_logo"], data["away_team_name"], data["away_team_score"]),
            spacing="1",
            margin_left=rx.breakpoints(initial="7px", md="20px"),
            margin_right=rx.breakpoints(initial="7px", md="20px")
        )
    )


def grid(mobile: bool):

    return rx.grid(
        rx.foreach(State.data, card),
        columns=("2" if mobile else "4"),
        spacing=("2" if mobile else "4")
    ),


@template(route="/live-scores", title="Live Scores", on_load=[State.set_gameweek, State.get_data])
def scores():
    return rx.flex(
        rx.heading("Live Scores"),
        rx.text(f"Gameweek {State.gameweek_id}", size="2"),
        rx.divider(width="100%"),
        rx.mobile_only(grid(True)),
        rx.tablet_and_desktop(grid(False)),
        spacing="4",
        direction="column",
        width="100%"
    )
