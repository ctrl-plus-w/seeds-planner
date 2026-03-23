import logging
import time
from collections.abc import Generator

import httpx

from scraper.config import BASE_URL, PAGE_SIZE, REQUEST_DELAY

logger = logging.getLogger("scraper")


class PermapeopleClient:
    def __init__(self, key_id: str, key_secret: str, delay: float = REQUEST_DELAY):
        self.delay = delay
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "x-permapeople-key-id": key_id,
                "x-permapeople-key-secret": key_secret,
            },
            timeout=30.0,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._client.close()

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.TransportError) as e:
                is_retryable = isinstance(e, httpx.TransportError) or (
                    isinstance(e, httpx.HTTPStatusError)
                    and e.response.status_code >= 500
                )
                if is_retryable and attempt < max_retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        max_retries,
                        wait,
                        e,
                    )
                    time.sleep(wait)
                    continue
                raise
        raise

    def get_plants_page(self, last_id: int | None = None) -> list[dict]:
        params = {}
        if last_id is not None:
            params["last_id"] = last_id
        logger.debug("GET /plants params=%s", params)
        response = self._request("GET", "/plants", params=params)
        return response.json()["plants"]

    def iter_all_plants(self) -> Generator[dict, None, None]:
        last_id = None
        page = 0
        while True:
            page += 1
            plants = self.get_plants_page(last_id=last_id)
            if not plants:
                break
            logger.info("Page %d: fetched %d plants", page, len(plants))
            yield from plants
            if len(plants) < PAGE_SIZE:
                break
            last_id = plants[-1]["id"]
            time.sleep(self.delay)
