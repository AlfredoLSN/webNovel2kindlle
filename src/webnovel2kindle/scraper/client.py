from __future__ import annotations

from dataclasses import dataclass

import httpx


class FetchError(RuntimeError):
    """Erro amigavel para falhas ao buscar uma pagina."""


@dataclass(frozen=True)
class HttpClient:
    timeout: float = 30.0

    def get_html(self, url: str) -> str:
        response = self._get(url)
        return response.text

    def get_bytes(self, url: str) -> tuple[bytes, str | None]:
        response = self._get(url)
        return response.content, response.headers.get("content-type")

    def _get(self, url: str) -> httpx.Response:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise FetchError(f"O site respondeu HTTP {status} ao buscar a obra.") from exc
        except httpx.HTTPError as exc:
            raise FetchError(f"Nao consegui buscar a pagina: {exc}") from exc

        return response
