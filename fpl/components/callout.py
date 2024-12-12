import reflex as rx


def callout(text: str) -> rx.Component:
    """
    Returns a callout
    """

    return rx.callout(
        text,
        icon="info",
        color_scheme="blue",
    )
