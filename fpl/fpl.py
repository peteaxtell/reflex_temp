from contextlib import asynccontextmanager

import reflex as rx
from fastapi import FastAPI

from . import styles
from .data.cache import cache_data
from .pages import *


@asynccontextmanager
async def startup(app: FastAPI):
    cache_data()
    yield

app = rx.App(style=styles.base_style, stylesheets=styles.base_stylesheets)
app.register_lifespan_task(startup)
