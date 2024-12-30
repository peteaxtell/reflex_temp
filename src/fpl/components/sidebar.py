"""Sidebar component for the app."""

import reflex as rx

from .. import styles


def sidebar_header() -> rx.Component:

    return rx.vstack(
        rx.color_mode_cond(
            rx.image(src="/logo_light_mode.png", height="10em"),
            rx.image(src="/logo_dark_mode.png", height="10em"),
        ),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )


def sidebar_footer() -> rx.Component:

    return rx.hstack(
        rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
        justify="start",
        align="center",
        width="100%",
        padding="0.35em",
    )


def sidebar_item(text: str, url: str, icon: str) -> rx.Component:

    active = (rx.State.router.page.path == url.lower()) | (
        (rx.State.router.page.path == "/") & text == "League Table"
    )

    return rx.link(
        rx.hstack(
            rx.cond(
                active,
                rx.image(src=f"/icons/{icon}_active.png", width="28px"),
                rx.color_mode_cond(
                    rx.image(src=f"/icons/{icon}_light_mode.png", width="28px"),
                    rx.image(src=f"/icons/{icon}_dark_mode.png", width="28px"),
                )
            ),
            rx.text(text, size="3", weight="regular"),
            color=rx.cond(
                active,
                styles.accent_text_color,
                styles.text_color,
            ),
            style={
                "_hover": {
                    "background_color": rx.cond(
                        active,
                        styles.accent_bg_color,
                        styles.gray_bg_color,
                    ),
                    "color": rx.cond(
                        active,
                        styles.accent_text_color,
                        styles.text_color,
                    ),
                    "opacity": "1",
                },
                "opacity": rx.cond(
                    active,
                    "1",
                    "0.95",
                ),
            },
            align="center",
            border_radius=styles.border_radius,
            width="100%",
            spacing="2",
            padding="0.35em",
        ),
        underline="none",
        href=url,
        width="100%",
    )


def sidebar() -> rx.Component:

    return rx.flex(
        rx.vstack(
            sidebar_header(),
            rx.vstack(
                sidebar_item("League Table", "/", "league"),
                sidebar_item("Live Scores", "/live-scores", "score"),
                sidebar_item("Live Updates", "/live-updates", "notification"),
                sidebar_item("Transfers", "/transfers", "transfer"),
                spacing="1",
                width="100%",
            ),
            rx.spacer(),
            sidebar_footer(),
            bg=styles.nav_bar_background_color,
            justify="end",
            align="end",
            width=styles.sidebar_content_width,
            height="100dvh",
            padding="1em",
            padding_top="2em"
        ),
        display=rx.breakpoints(initial="none", md="flex"),
        max_width=styles.sidebar_width,
        width="auto",
        height="100%",
        position="sticky",
        justify="end",
        top="0px",
        left="0px",
        flex="1",
        bg=rx.color("gray", 2)
    )
