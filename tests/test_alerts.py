import httpx

from arbitrage_monitor.alerts import ConsoleNotifier, TelegramNotifier, format_alert, strip_html
from tests.conftest import make_opp


def test_format_contains_route_and_numbers():
    text = format_alert(make_opp(), 1000)
    assert "BTC/USDT" in text
    assert "binance:spot" in text and "bybit:spot" in text
    assert "100.0000" in text and "105.0000" in text
    assert "4.78%" in text
    assert "500,000.00 USDT" in text
    assert "1000 USDT" in text


def test_format_states_informational_only():
    assert "Informational only" in format_alert(make_opp(), 1000)


def test_format_escapes_html_in_names():
    text = format_alert(make_opp(symbol="A<B>/USDT", buy_venue="x&y"), 1000)
    assert "A&lt;B&gt;/USDT" in text
    assert "x&amp;y" in text


def test_strip_html_removes_tags_and_unescapes():
    assert strip_html("<b>a &amp; b</b> <i>c</i>") == "a & b c"


async def test_console_notifier_prints(capsys):
    assert await ConsoleNotifier().send("<b>hello</b>") is True
    assert "hello" in capsys.readouterr().out


def make_client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_telegram_sends_expected_payload():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"ok": True})

    notifier = TelegramNotifier("tok", "123", make_client(handler))
    assert await notifier.send("hi") is True
    assert seen["url"] == "https://api.telegram.org/bottok/sendMessage"
    assert "chat_id=123" in seen["body"] and "parse_mode=HTML" in seen["body"]


async def test_telegram_http_error_status_returns_false():
    notifier = TelegramNotifier("tok", "1", make_client(lambda r: httpx.Response(400)))
    assert await notifier.send("hi") is False


async def test_telegram_network_error_returns_false():
    def handler(request):
        raise httpx.ConnectError("boom")

    notifier = TelegramNotifier("tok", "1", make_client(handler))
    assert await notifier.send("hi") is False


async def test_telegram_failure_log_does_not_leak_token(caplog):
    def handler(request):
        raise httpx.ConnectError("https://api.telegram.org/botSECRET/sendMessage")

    notifier = TelegramNotifier("SECRET", "1", make_client(handler))
    await notifier.send("hi")
    assert "SECRET" not in caplog.text
