import asyncio
import time
from dataclasses import dataclass

import httpx


@dataclass
class CheckResult:
    name: str
    url: str
    status: str        # OK | ERROR | TIMEOUT
    latency_ms: float
    status_code: int | None = None


async def _check_one(client: httpx.AsyncClient, name: str, url: str, timeout: float = 5.0) -> CheckResult:
    start = time.monotonic()
    try:
        response = await client.get(url, timeout=timeout, follow_redirects=True)
        latency_ms = (time.monotonic() - start) * 1000
        status = "OK" if response.status_code < 400 else "ERROR"
        return CheckResult(name=name, url=url, status=status,
                           latency_ms=latency_ms, status_code=response.status_code)
    except httpx.TimeoutException:
        latency_ms = (time.monotonic() - start) * 1000
        return CheckResult(name=name, url=url, status="TIMEOUT", latency_ms=latency_ms)
    except httpx.RequestError:
        latency_ms = (time.monotonic() - start) * 1000
        return CheckResult(name=name, url=url, status="ERROR", latency_ms=latency_ms)


async def check_all_endpoints(endpoints: list[dict]) -> list[CheckResult]:
    async with httpx.AsyncClient() as client:
        tasks = [_check_one(client, ep["name"], ep["url"]) for ep in endpoints]
        return await asyncio.gather(*tasks)
