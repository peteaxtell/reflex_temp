import dataclasses

import reflex as rx


@dataclasses.dataclass
class League:
    id: str
    name: str


class LeagueSelectState(rx.State):

    leagues: list[League] = [
        League(id="464405", name="SS Ladzio league"),
        League(id="737576", name="The Ladzio Memorial Cup"),
        League(id="1643181", name="The Oscar & Milo Championship"),
    ]

    selected_league: League | None = None

    def set_selected_league(self, league_id: str):
        self.selected_league = next((l for l in self.leagues if l.id == league_id), None)

    @rx.event
    def handle_submit(self, form_data: dict):
        self.set_selected_league(form_data["selected"])


def league_badge() -> rx.Component:
    """
    Returns a badge showing the selected league
    """

    return rx.center(
        rx.flex(
            rx.badge(LeagueSelectState.selected_league.name, margin="2", size="2"),
            league_dialog(),
            spacing="2",
            width="100%"
        )
    )


def league_dialog() -> rx.Component:
    """
    Returns a dialog for selecting a league
    """

    return rx.dialog.root(
        rx.dialog.trigger(rx.icon_button("settings", variant="outline", size="1")),
        rx.dialog.content(
            rx.form.root(
                rx.flex(
                    rx.select.root(
                        rx.select.trigger(placeholder="Select a league"),
                        rx.select.content(
                            rx.select.group(
                                rx.foreach(
                                    LeagueSelectState.leagues,
                                    lambda x: rx.select.item(
                                        x.name, value=x.id
                                    ),
                                )
                            ),
                        ),
                        default_value=LeagueSelectState.selected_league.id,
                        name="selected",
                        width="100%"
                    ),
                    rx.hstack(
                        rx.button(
                            "Save",
                            type="submit",
                            height="30px",
                            width="70px",
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Close",
                                height="30px",
                                width="70px",
                            ),
                        ),
                        justify="end",
                    ),
                    direction="column",
                    spacing="3",
                ),
                on_submit=LeagueSelectState.handle_submit
            )
        )
    )