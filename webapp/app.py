from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from webapp.constants import SECRET_KEY
from webapp.routes import web

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.register_blueprint(web)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
