import reflex as rx

from .league_selector import selected_league_badge


def page_header(title: str, gameweek: int) -> rx.Component:
    """
    Returns page title and current gameweek
    """

    return rx.fragment(
        rx.heading(title),
        rx.text(f"Gameweek {gameweek}", size="2"),
        selected_league_badge(),
        rx.divider(width="100%")
    )
