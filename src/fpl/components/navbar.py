"""Sidebar component for the app."""

import reflex as rx

from .. import styles


def navbar_item(url: str, icon: str) -> rx.Component:

    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & icon == "ordered-list"
    )

    return rx.link(
        rx.cond(
            active,
            rx.image(src=f"/icons/{icon}_active.png", width="28px"),
            rx.color_mode_cond(
                rx.image(src=f"/icons/{icon}_light_mode.png", width="28px"),
                rx.image(src=f"/icons/{icon}_dark_mode.png", width="28px"),
            )
        ),
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

    from reflex.page import get_decorated_pages

    return rx.flex(
        rx.hstack(
            navbar_item("/", "league"),
            navbar_item("/live-scores", "score"),
            navbar_item("/live-updates", "notification"),
            navbar_item("/transfers", "transfer"),
            rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
            align="center",
            justify="center",
            width="100%",
            height="4em",
            padding="1em",
            spacing="7"
        ),
        display=rx.breakpoints(initial="flex", md="none"),
        width="100%",
        height="100%",
        position="sticky",
        justify="end",
        bottom="0px",
        left="0px",
        flex="1",
        bg=rx.color("gray", 2),
    )
