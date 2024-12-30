"""Styles for the app."""

import reflex as rx

background_color = rx.color_mode_cond(rx.color("gray", 1), "#212830")
nav_bar_background_color = rx.color_mode_cond(rx.color("gray", 4), "#151b23")
border_radius = "var(--radius-2)"
border = f"1px solid {rx.color('gray', 5)}"
text_color = rx.color("gray", 11)
gray_color = rx.color("gray", 11)
gray_bg_color = rx.color("gray", 3)
accent_text_color = rx.color("accent", 10)
accent_color = rx.color("accent", 1)
accent_bg_color = rx.color("accent", 3)
sidebar_width = "16em"
sidebar_content_width = "16em"
max_width = "1480px"

template_content_style = {
    "height": rx.breakpoints(initial="calc(100dvh - 4em)", md="100dvh"),
    "overflow": "auto",
    "padding": "2em",
    "width": "100%"
}

base_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    "style.css"
]

base_style = {
    "font_family": "Inter",
}
