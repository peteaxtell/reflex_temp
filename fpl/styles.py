"""Styles for the app."""

import reflex as rx

border_radius = "var(--radius-2)"
border = f"1px solid {rx.color('gray', 5)}"
text_color = rx.color("gray", 11)
gray_color = rx.color("gray", 11)
gray_bg_color = rx.color("gray", 3)
accent_text_color = rx.color("accent", 10)
accent_color = rx.color("accent", 1)
accent_bg_color = rx.color("accent", 3)
content_width_vw = "90vw"
sidebar_width = "16em"
sidebar_content_width = "16em"
max_width = "1480px"

template_page_style = {
    "padding_top": ["1em", "1em", "2em"],
    "padding_x": ["auto", "auto", "2em"],
}

template_content_style = {
    "padding": "1em",
    "margin_bottom": "2em",
    "min_height": "90vh",
}

base_stylesheets = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
    "style.css"
]

base_style = {
    "font_family": "Inter",
}
