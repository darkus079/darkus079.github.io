from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from config import settings, state


class BackendClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = None):
        self._base_url = (base_url or state.backend_base_url).rstrip("/")
        self._timeout = timeout or settings.REQUEST_TIMEOUT_SECONDS
        self._client = httpx.AsyncClient(timeout=self._timeout)

    @property
    def base_url(self) -> str:
        return self._base_url

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> Dict[str, Any]:
        url = f"{self._base_url}/api/health"
        r = await self._client.get(url)
        r.raise_for_status()
        return r.json()

    async def parse(self, case_number: str) -> Dict[str, Any]:
        url = f"{self._base_url}/api/parse"
        payload = {"case_number": case_number}
        r = await self._client.post(url, json=payload)
        r.raise_for_status()
        return r.json()

    async def status(self) -> Dict[str, Any]:
        url = f"{self._base_url}/api/status"
        r = await self._client.get(url)
        r.raise_for_status()
        return r.json()

    async def links(self, case_number: str) -> Dict[str, Any]:
        url = f"{self._base_url}/api/links"
        r = await self._client.get(url, params={"case": case_number})
        r.raise_for_status()
        return r.json()

    async def cases(self) -> Dict[str, Any]:
        url = f"{self._base_url}/api/cases"
        r = await self._client.get(url)
        r.raise_for_status()
        return r.json()

    async def diagnostics(self) -> str:
        # Returns HTML page; use plain text mention
        url = f"{self._base_url}/diagnostics"
        r = await self._client.get(url)
        r.raise_for_status()
        return r.text

    async def reinit(self) -> Dict[str, Any]:
        url = f"{self._base_url}/reinit-driver"
        r = await self._client.get(url)
        r.raise_for_status()
        return r.json()


client_singleton: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    global client_singleton
    if client_singleton is None:
        client_singleton = BackendClient()
    return client_singleton


