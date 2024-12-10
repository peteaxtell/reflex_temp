"""Sidebar component for the app."""

import reflex as rx

from .. import styles


def navbar_item(url: str, icon: str) -> rx.Component:
    """Sidebar item.

    Args:
        text: The text of the item.
        url: The URL of the item.

    Returns:
        rx.Component: The sidebar item component.
    """
    # Whether the item is active.
    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & icon == "ordered-list"
    )

    return rx.link(
        rx.icon(icon, size=22),
        color=rx.cond(
            active,
            styles.accent_text_color,
            styles.text_color,
        ),
        style={
            "opacity": rx.cond(
                active,
                "1",
                "0.95",
            ),
        },
        underline="none",
        href=url
    )


def navbar() -> rx.Component:
    """The sidebar.

    Returns:
        The sidebar component.
    """
    # Get all the decorated pages and add them to the sidebar.
    from reflex.page import get_decorated_pages

    return rx.flex(
        rx.hstack(
            navbar_item("/", "list-ordered"),
            navbar_item("/live-scores", "goal"),
            navbar_item("/live-updates", "rss"),
            rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
            align="center",
            justify="center",
            width="100%",
            height="4em",
            padding="1em",
            spacing="7"
        ),
        display=["flex", "flex", "flex", "none", "none", "none"],
        width="100%",
        height="100%",
        position="sticky",
        justify="end",
        bottom="0px",
        left="0px",
        flex="1",
        bg=rx.color("gray", 2),
    )
