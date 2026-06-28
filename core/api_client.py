import json
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_TOKEN_PATH = Path.home() / ".faktur" / "token.json"
DEFAULT_BASE_URL = "http://localhost:3000"


class ApiClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, token_path: Path = DEFAULT_TOKEN_PATH):
        self._base = base_url.rstrip("/")
        self._token_path = token_path
        self._token: dict | None = self._load_token()

    def _load_token(self) -> dict | None:
        if self._token_path.exists():
            try:
                return json.loads(self._token_path.read_text())
            except Exception:
                return None
        return None

    def _save_token(self, token_data: dict):
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(json.dumps(token_data))
        self._token = token_data

    def is_authenticated(self) -> bool:
        if not self._token:
            return False
        try:
            expires_at = datetime.fromisoformat(self._token["expires_at"])
            return expires_at > datetime.now(timezone.utc)
        except (KeyError, ValueError):
            return False

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token['access_token']}"}

    def login(self, email: str, password: str) -> dict:
        resp = requests.post(f"{self._base}/auth/login", json={"email": email, "password": password}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=14)).isoformat()
        self._save_token({**data, "expires_at": expires_at})
        return data

    def get_me(self) -> dict:
        resp = requests.get(f"{self._base}/me", headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_quota(self) -> dict:
        resp = requests.get(f"{self._base}/usage/quota", headers=self._auth_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def report_usage(self, files_processed: int) -> dict:
        resp = requests.post(
            f"{self._base}/usage/report",
            json={"files_processed": files_processed},
            headers=self._auth_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def logout(self):
        if self._token_path.exists():
            self._token_path.unlink()
        self._token = None
