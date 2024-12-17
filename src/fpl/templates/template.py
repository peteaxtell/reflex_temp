from __future__ import annotations

from typing import Callable

import reflex as rx

from .. import styles
from ..components.navbar import navbar
from ..components.sidebar import sidebar

default_meta = [
    {
        "name": "viewport",
        "content": "width=device-width, shrink-to-fit=no, initial-scale=1",
    },
]


class ThemeState(rx.State):

    accent_color: str = "blue"
    gray_color: str = "gray"
    radius: str = "large"
    scaling: str = "100%"


def template(
    route: str | None = None,
    title: str | None = None,
    description: str | None = None,
    meta: str | None = None,
    script_tags: list[rx.Component] | None = None,
    on_load: rx.EventHandler | list[rx.EventHandler] | None = None,
) -> Callable[[Callable[[], rx.Component]], rx.Component]:

    def decorator(page_content: Callable[[], rx.Component]) -> rx.Component:
        all_meta = [*default_meta, *(meta or [])]

        def templated_page():
            return rx.flex(
                sidebar(),
                rx.box(
                    page_content(),
                    flex_grow=1,
                    **styles.template_content_style,
                ),
                navbar(),
                flex_direction=rx.breakpoints(initial="column", md="row"),
                width="100%",
                margin="auto",
                position="relative",
            ),

        @rx.page(
            route=route,
            title=title,
            description=description,
            meta=all_meta,
            script_tags=script_tags,
            on_load=on_load,
        )
        def theme_wrap():
            return rx.theme(
                templated_page(),
                accent_color=ThemeState.accent_color,
                gray_color=ThemeState.gray_color,
                has_background=True,
                radius=ThemeState.radius,
                scaling=ThemeState.scaling,
            )

        return theme_wrap

    return decorator
