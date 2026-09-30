from __future__ import annotations

import re


class Resp:
    def __init__(self, data, status=200, headers=None):
        self._data, self.status_code, self.headers = data, status, headers or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHTTP:
    """Routes requests by regex on the URL to canned JSON; records every call."""

    def __init__(self, routes: dict[str, object]):
        self.routes = routes
        self.calls: list[tuple[str, str, dict]] = []

    def _match(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for pat, data in self.routes.items():
            if re.search(pat, url):
                return data(url, kw) if callable(data) else Resp(data)
        return Resp({}, 404)

    def get(self, url, **kw):
        return self._match("GET", url, **kw)

    def post(self, url, **kw):
        return self._match("POST", url, **kw)

    def put(self, url, **kw):
        return self._match("PUT", url, **kw)
