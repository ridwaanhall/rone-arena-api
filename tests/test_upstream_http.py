from __future__ import annotations

import httpx
import pytest

from app.core import http as upstream
from app.core.exceptions import AppError

WAF_PAGE = httpx.Response(405, headers={"content-type": "text/html; charset=utf-8"}, text="<title>405</title>")


def _client_answering(*responses: httpx.Response) -> tuple[httpx.Client, list[int]]:
    calls: list[int] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


def test_waf_block_is_retried_once(monkeypatch) -> None:
    client, calls = _client_answering(WAF_PAGE, httpx.Response(200, json={"code": 0}))
    monkeypatch.setattr(upstream, "_get_client", lambda: client)

    assert upstream.request_json(method="POST", url="https://upstream.test/x", headers={}) == {"code": 0}
    assert len(calls) == 2


def test_persistent_waf_block_is_reported_as_rate_limited(monkeypatch) -> None:
    client, calls = _client_answering(WAF_PAGE)
    monkeypatch.setattr(upstream, "_get_client", lambda: client)

    with pytest.raises(AppError) as caught:
        upstream.request_json(method="POST", url="https://upstream.test/x", headers={})

    assert caught.value.status_code == 429
    assert caught.value.code == "UPSTREAM_RATE_LIMITED"
    assert len(calls) == 2


def test_json_405_is_not_treated_as_a_waf_block(monkeypatch) -> None:
    client, calls = _client_answering(httpx.Response(405, json={"error": "nope"}))
    monkeypatch.setattr(upstream, "_get_client", lambda: client)

    with pytest.raises(AppError) as caught:
        upstream.request_json(method="GET", url="https://upstream.test/x", headers={})

    assert caught.value.status_code == 405
    assert len(calls) == 1


def test_request_page_returns_the_response_for_html_and_cookie_access(monkeypatch) -> None:
    client, _ = _client_answering(httpx.Response(200, headers={"set-cookie": "session=abc"}, text="<html>ok</html>"))
    monkeypatch.setattr(upstream, "_get_client", lambda: client)

    response = upstream.request_page(method="GET", url="https://upstream.test/page", headers={})

    assert response.text == "<html>ok</html>"
    assert response.headers["set-cookie"] == "session=abc"


def test_request_page_shares_the_waf_retry_and_error_mapping(monkeypatch) -> None:
    client, calls = _client_answering(WAF_PAGE, httpx.Response(200, text="<html></html>"))
    monkeypatch.setattr(upstream, "_get_client", lambda: client)
    assert upstream.request_page(method="GET", url="https://upstream.test/page", headers={}).text == "<html></html>"
    assert len(calls) == 2

    client, _ = _client_answering(httpx.Response(404, text="missing"))
    monkeypatch.setattr(upstream, "_get_client", lambda: client)
    with pytest.raises(AppError) as caught:
        upstream.request_page(method="GET", url="https://upstream.test/page", headers={})
    assert caught.value.status_code == 404
