import reflex as rx


def page_header(title: str, gameweek: int) -> rx.Component:
    """
    Returns page title and current gameweek
    """

    return rx.fragment(
        rx.heading(title),
        rx.text(f"Gameweek {gameweek}", size="2"),
        rx.divider(width="100%")
    )
