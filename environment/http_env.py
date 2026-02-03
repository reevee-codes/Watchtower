import random
import time
import httpx

URLS = [
    "https://httpbin.org/status/200",
    "https://httpbin.org/status/500",
    "https://httpbin.org/delay/2",
]


async def check_api(timeout_s: float = 2.0) -> tuple[str, float]:
    url = random.choice(URLS)
    start = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.get(url)
        latency_ms = (time.perf_counter() - start) * 1000.0

        if r.status_code == 200:
            return "OK", latency_ms
        return "ERROR", latency_ms

    except httpx.RequestError:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return "TIMEOUT", latency_ms
