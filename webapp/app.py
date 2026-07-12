from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask import url_for

from .constants import SECRET_KEY
from .routes import web


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["ENV_TYPE"] = os.getenv("ENV_TYPE", "dev").strip().lower()
    app.config["STATIC_BASE_URL"] = os.getenv("STATIC_BASE_URL", "").strip().rstrip("/")
    app.config["URL_PREFIX"] = os.getenv("URL_PREFIX", "").strip()

    @app.context_processor
    def inject_static_asset_url() -> dict[str, object]:
        env_type = str(app.config.get("ENV_TYPE", "dev")).lower()
        static_base_url = str(app.config.get("STATIC_BASE_URL", "")).rstrip("/")

        def static_asset_url(filename: str) -> str:
            clean_filename = filename.lstrip("/")
            if env_type == "prod" and static_base_url:
                return f"{static_base_url}/{clean_filename}"
            return url_for("static", filename=clean_filename)

        return {"static_asset_url": static_asset_url}

    app.register_blueprint(web)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=app.config.get("ENV_TYPE") != "prod", host="127.0.0.1", port=5000)
