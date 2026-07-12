from __future__ import annotations

from flask import Flask
from flask import Request
from flask.typing import ResponseReturnValue

from webapp.app import create_app


app = create_app()


# functions-framework --target=entry_point --debug
def entry_point(request: Request) -> ResponseReturnValue:
    """Cloud Functions HTTP entry point that dispatches via the Flask app."""
    with app.request_context(request.environ):
        return app.full_dispatch_request()


if __name__ == "__main__":
    app.run(debug=app.config.get("ENV_TYPE") != "prod", host="127.0.0.1", port=5000)