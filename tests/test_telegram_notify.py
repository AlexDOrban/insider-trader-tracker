from unittest.mock import patch, MagicMock
import pytest

from telegram_notify import send_message, TelegramError


def test_send_message_posts_to_correct_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    with patch("telegram_notify.requests.post") as post:
        post.return_value = MagicMock(status_code=200, content=b"{}", json=lambda: {"ok": True})
        send_message("hello")
        url = post.call_args.args[0]
        assert "TOK" in url
        assert url.endswith("/sendMessage")
        payload = post.call_args.kwargs["json"]
        assert payload["chat_id"] == "123"
        assert payload["text"] == "hello"
        assert payload["parse_mode"] == "HTML"


def test_send_message_raises_on_telegram_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    with patch("telegram_notify.requests.post") as post:
        post.return_value = MagicMock(
            status_code=400, content=b"{}",
            json=lambda: {"ok": False, "description": "bad"},
        )
        with pytest.raises(TelegramError, match="bad"):
            send_message("hello")


def test_send_message_missing_env_raises(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(TelegramError, match="TELEGRAM_BOT_TOKEN"):
        send_message("hello")
