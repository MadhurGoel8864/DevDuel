from uvicorn.workers import UvicornWorker

class CustomUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {
        "ws_ping_interval": 20,
        "ws_ping_timeout": 10,
    }
