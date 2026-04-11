import json
import logging
import os
import sys

from flask import Flask, redirect, render_template, request, session, url_for
from flask_cors import CORS
from google_auth_oauthlib.flow import Flow

# Permite que o projeto seja importado independente do cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.config import load_config, save_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(32)
CORS(app)

REDIRECT_URI = "http://localhost:5001/oauth/callback"
SCOPES = ["https://www.googleapis.com/auth/adwords"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_statuses(current: int) -> list[str]:
    """Retorna lista de status ('done'|'active'|'pending') para os 4 steps."""
    statuses = []
    for i in range(1, 5):
        if i < current:
            statuses.append("done")
        elif i == current:
            statuses.append("active")
        else:
            statuses.append("pending")
    return statuses


def _build_oauth_flow(config: dict) -> Flow:
    client_config = {
        "web": {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("step", n=1))


@app.route("/step/<int:n>", methods=["GET", "POST"])
def step(n: int):
    if n not in range(1, 5):
        return redirect(url_for("step", n=1))

    config = load_config()
    error = None
    success_msg = None

    if request.method == "POST":
        # ---- Step 1: Google Cloud Credentials ----
        if n == 1:
            raw = request.form.get("credentials_json", "").strip()
            try:
                creds = json.loads(raw)
                # Suporta formato "installed" ou "web"
                inner = creds.get("installed") or creds.get("web") or creds
                client_id = inner.get("client_id", "")
                client_secret = inner.get("client_secret", "")
                if not client_id or not client_secret:
                    raise ValueError("client_id ou client_secret ausentes.")
                config["client_id"] = client_id
                config["client_secret"] = client_secret
                save_config(config)
                return redirect(url_for("step", n=2))
            except (json.JSONDecodeError, ValueError) as e:
                error = f"JSON inválido: {e}"

        # ---- Step 2: Developer Token ----
        elif n == 2:
            dev_token = request.form.get("developer_token", "").strip()
            test_account = request.form.get("test_account") == "on"
            if not dev_token:
                error = "Developer Token é obrigatório."
            else:
                config["developer_token"] = dev_token
                config["test_account"] = test_account
                save_config(config)
                return redirect(url_for("step", n=3))

        # ---- Step 4: Customer ID ----
        elif n == 4:
            customer_id = request.form.get("customer_id", "").strip().replace("-", "")
            login_customer_id = request.form.get("login_customer_id", "").strip().replace("-", "")
            if not customer_id or not customer_id.isdigit():
                error = "Customer ID inválido. Use apenas dígitos ou o formato xxx-xxx-xxxx."
            else:
                config["customer_id"] = customer_id
                config["login_customer_id"] = login_customer_id
                save_config(config)
                return redirect(url_for("success"))

    return render_template(
        f"step_{['credentials', 'developer_token', 'oauth', 'customer_id'][n - 1]}.html",
        step=n,
        statuses=_step_statuses(n),
        config=config,
        error=error,
        success_msg=success_msg,
    )


@app.route("/oauth/start")
def oauth_start():
    config = load_config()
    if not config.get("client_id") or not config.get("client_secret"):
        return redirect(url_for("step", n=1))

    flow = _build_oauth_flow(config)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    session["oauth_state"] = state
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    config = load_config()
    state = session.get("oauth_state")

    try:
        flow = _build_oauth_flow(config)
        flow.fetch_token(
            authorization_response=request.url.replace("http://", "https://")
            if request.url.startswith("http://localhost")
            else request.url,
            code=request.args.get("code"),
        )
        refresh_token = flow.credentials.refresh_token
        if not refresh_token:
            raise ValueError("Refresh token não retornado. Tente revogar o acesso e autorizar novamente.")
        config["refresh_token"] = refresh_token
        save_config(config)
        session["oauth_done"] = True
        logger.info("OAuth concluído — refresh_token salvo.")
        return redirect(url_for("step", n=4))
    except Exception as e:
        logger.error("Erro no OAuth callback: %s", e)
        session["oauth_error"] = str(e)
        return redirect(url_for("step", n=3))


@app.route("/test-connection", methods=["POST"])
def test_connection():
    """Testa a conexão com a Google Ads API."""
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    config = load_config()
    customer_id = request.json.get("customer_id", config.get("customer_id", "")).replace("-", "")

    try:
        client_config = {
            "developer_token": config["developer_token"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "refresh_token": config["refresh_token"],
            "use_proto_plus": True,
        }
        if config.get("login_customer_id"):
            client_config["login_customer_id"] = config["login_customer_id"]

        client = GoogleAdsClient.load_from_dict(client_config)
        customer_service = client.get_service("CustomerService")
        resource_name = customer_service.customer_path(customer_id)

        ga_service = client.get_service("GoogleAdsService")
        query = "SELECT customer.descriptive_name, customer.currency_code FROM customer LIMIT 1"
        response = ga_service.search(customer_id=customer_id, query=query)

        for row in response:
            return {
                "ok": True,
                "account_name": row.customer.descriptive_name,
                "currency": row.customer.currency_code,
            }

        return {"ok": True, "account_name": "Conta acessível", "currency": "BRL"}

    except GoogleAdsException as e:
        errors = [err.message for err in e.failure.errors]
        return {"ok": False, "error": "; ".join(errors)}, 400
    except Exception as e:
        return {"ok": False, "error": str(e)}, 400


@app.route("/success")
def success():
    config = load_config()
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    server_path = os.path.join(project_path, "server.py")
    venv_python = os.path.join(project_path, ".venv", "bin", "python")

    mcp_config = {
        "mcpServers": {
            "google-ads": {
                "command": venv_python,
                "args": [server_path],
                "env": {},
            }
        }
    }

    return render_template(
        "success.html",
        config=config,
        mcp_config_json=json.dumps(mcp_config, indent=2),
        statuses=["done", "done", "done", "done"],
    )


if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app.run(host="localhost", port=5001, debug=False)
