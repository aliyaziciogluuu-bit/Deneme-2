"""Kibar ve dayanıklı HTTP istemcisi.

Tüm veri kaynakları bu istemciden geçer: tekrar deneme (üstel bekleme), zaman aşımı,
sunucu başına asgari istek aralığı ve tanımlı bir User-Agent.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


class HttpError(RuntimeError):
    """Tekrar denemelere rağmen başarısız olan istek."""


class HttpClient:
    """İş parçacığı güvenli, sunucu başına hız sınırlı GET istemcisi."""

    def __init__(
        self,
        min_interval: float = 0.15,
        timeout: float = 60.0,
        retries: int = 4,
        backoff: float = 1.5,
    ) -> None:
        self.min_interval = min_interval
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._local = threading.local()
        self._lock = threading.Lock()
        self._next_slot: dict[str, float] = {}

    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update(
                {
                    "User-Agent": USER_AGENT,
                    "Accept": "*/*",
                    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                }
            )
            self._local.session = s
        return s

    def _throttle(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot.get(host, 0.0))
            self._next_slot[host] = slot + self.min_interval
        wait = slot - now
        if wait > 0:
            time.sleep(wait)

    def get(
        self,
        url: str,
        params: dict | None = None,
        ok_statuses: tuple[int, ...] = (200,),
        missing_statuses: tuple[int, ...] = (404,),
    ) -> requests.Response | None:
        """GET isteği yapar.

        ``missing_statuses`` içindeki bir kod dönerse ``None`` döner (kaynak yok demektir);
        diğer hatalarda tekrar dener, sonunda ``HttpError`` fırlatır.
        """
        return self._request("GET", url, ok_statuses, missing_statuses, params=params)

    def post_json(self, url: str, body: dict) -> requests.Response:
        """JSON gövdeli POST isteği (ASP.NET ``.aspx/Metot`` uçları için)."""
        resp = self._request(
            "POST", url, (200,), (),
            json=body,
            headers={"Content-Type": "application/json; charset=UTF-8", "X-Requested-With": "XMLHttpRequest"},
        )
        assert resp is not None
        return resp

    def _request(
        self,
        method: str,
        url: str,
        ok_statuses: tuple[int, ...],
        missing_statuses: tuple[int, ...],
        **kwargs,
    ) -> requests.Response | None:
        host = urlsplit(url).netloc
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            self._throttle(host)
            try:
                resp = self._session().request(method, url, timeout=self.timeout, **kwargs)
                if resp.status_code in ok_statuses:
                    return resp
                if resp.status_code in missing_statuses:
                    return None
                last_exc = HttpError(f"HTTP {resp.status_code} {url}")
            except requests.RequestException as exc:  # ağ hatası, zaman aşımı vb.
                last_exc = exc
            if attempt < self.retries:
                delay = self.backoff * (2**attempt) * (0.75 + 0.5 * random.random())
                log.debug("yeniden deneme %s/%s (%s) %.1fs sonra", attempt + 1, self.retries, url, delay)
                time.sleep(delay)
        raise HttpError(f"istek başarısız: {url}: {last_exc}")
