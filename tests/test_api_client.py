import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.api_client import ApiClient


@pytest.fixture
def tmp_token_path(tmp_path):
    return tmp_path / "token.json"


def test_is_authenticated_false_when_no_token(tmp_token_path):
    client = ApiClient(base_url="http://test", token_path=tmp_token_path)
    assert client.is_authenticated() is False


def test_is_authenticated_true_when_valid_token(tmp_token_path):
    from datetime import datetime, timedelta, timezone
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tmp_token_path.write_text(json.dumps({"access_token": "tok", "refresh_token": "ref", "expires_at": expires}))
    client = ApiClient(base_url="http://test", token_path=tmp_token_path)
    assert client.is_authenticated() is True


def test_login_saves_token(tmp_token_path):
    client = ApiClient(base_url="http://test", token_path=tmp_token_path)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "acc", "refresh_token": "ref", "token_type": "bearer"}
    mock_resp.raise_for_status = MagicMock()

    with patch("core.api_client.requests.post", return_value=mock_resp):
        client.login("a@b.com", "pass")

    assert tmp_token_path.exists()
    saved = json.loads(tmp_token_path.read_text())
    assert saved["access_token"] == "acc"


def test_get_quota_returns_dict(tmp_token_path):
    from datetime import datetime, timedelta, timezone
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tmp_token_path.write_text(json.dumps({"access_token": "tok", "refresh_token": "ref", "expires_at": expires}))
    client = ApiClient(base_url="http://test", token_path=tmp_token_path)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"remaining": 40, "limit": 50, "used": 10}
    mock_resp.raise_for_status = MagicMock()

    with patch("core.api_client.requests.get", return_value=mock_resp):
        quota = client.get_quota()

    assert quota["remaining"] == 40


def test_report_usage_posts_count(tmp_token_path):
    from datetime import datetime, timedelta, timezone
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tmp_token_path.write_text(json.dumps({"access_token": "tok", "refresh_token": "ref", "expires_at": expires}))
    client = ApiClient(base_url="http://test", token_path=tmp_token_path)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"remaining": 30, "limit": 50, "used": 20}
    mock_resp.raise_for_status = MagicMock()

    with patch("core.api_client.requests.post", return_value=mock_resp) as mock_post:
        result = client.report_usage(10)

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert call_kwargs[1]["json"]["files_processed"] == 10
    assert result["remaining"] == 30
