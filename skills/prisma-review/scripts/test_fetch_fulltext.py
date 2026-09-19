import pytest
from fetch_fulltext import is_safe_url, download_fulltext, enrich_records_with_fulltext

def test_is_safe_url_rejects_http():
    assert is_safe_url("http://example.org/paper.pdf") is False

def test_is_safe_url_rejects_private_ip(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                         lambda *a, **kw: [(None, None, None, None, ("127.0.0.1", 443))])
    assert is_safe_url("https://internal.example/paper.pdf") is False

def test_is_safe_url_accepts_public_https(monkeypatch):
    import socket
    monkeypatch.setattr(socket, "getaddrinfo",
                         lambda *a, **kw: [(None, None, None, None, ("93.184.216.34", 443))])
    assert is_safe_url("https://example.org/paper.pdf") is True

def test_download_fulltext_rejects_non_pdf_content_type(tmp_path, monkeypatch):
    import fetch_fulltext
    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "text/html"}
        def iter_content(self, chunk_size): return [b"<html>"]
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(fetch_fulltext, "is_safe_url", lambda url: True)
    monkeypatch.setattr(fetch_fulltext.requests, "get", lambda *a, **kw: FakeResponse())
    result = download_fulltext("https://example.org/paper.pdf", tmp_path, "rec1")
    assert result is None

def test_download_fulltext_rejects_oversize(tmp_path, monkeypatch):
    import fetch_fulltext
    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "application/pdf"}
        def iter_content(self, chunk_size): return [b"x" * chunk_size for _ in range(3)]
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(fetch_fulltext, "is_safe_url", lambda url: True)
    monkeypatch.setattr(fetch_fulltext.requests, "get", lambda *a, **kw: FakeResponse())
    result = download_fulltext("https://example.org/paper.pdf", tmp_path, "rec1", max_bytes=10)
    assert result is None
    assert list(tmp_path.iterdir()) == []  # partial file cleaned up

def test_download_fulltext_rejects_redirect(tmp_path, monkeypatch):
    import fetch_fulltext
    class FakeResponse:
        status_code = 302
        headers = {"Location": "http://169.254.169.254/"}
        def iter_content(self, chunk_size): return [b"should-not-be-read"]
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    captured = {}
    def fake_get(*a, **kw):
        captured["allow_redirects"] = kw.get("allow_redirects")
        return FakeResponse()
    monkeypatch.setattr(fetch_fulltext, "is_safe_url", lambda url: True)
    monkeypatch.setattr(fetch_fulltext.requests, "get", fake_get)
    result = download_fulltext("https://example.org/paper.pdf", tmp_path, "rec1")
    assert result is None
    assert captured["allow_redirects"] is False
    assert list(tmp_path.iterdir()) == []

def test_enrich_records_sets_local_pdf_path_none_on_missing_url(tmp_path):
    records = [{"id": "r1", "title": "No URL here"}]
    enriched = enrich_records_with_fulltext(records, tmp_path)
    assert enriched[0]["local_pdf_path"] is None
