import reflex as rx

config = rx.Config(
    app_name="fpl",
    state_manager_mode="memory",
    backend_port=8001,
    frontend_port=4000,
    # api_url="http://fpl.axtellcloud.com:8000"
)
