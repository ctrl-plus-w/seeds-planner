import logging
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from scraper.config import REQUEST_DELAY, SITE_URL

logger = logging.getLogger("scraper")


def parse_relationships(html: str) -> dict[str, list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, list[dict]] = {"companions": [], "antagonists": []}

    for h5 in soup.find_all("h5"):
        text = h5.get_text(strip=True).lower()
        if "companion" in text:
            key = "companions"
        elif "antagonist" in text:
            key = "antagonists"
        else:
            continue

        # Collect all <a> siblings after this h5 within the same parent
        container = h5.parent
        if not container:
            continue

        for a_tag in container.find_all("a", href=True):
            href = a_tag["href"]
            path = urlparse(href).path
            if not path.startswith("/plants/"):
                continue
            slug = path.removeprefix("/plants/")

            label = a_tag.find("label")
            if label:
                span = label.find("span")
                scientific_name = span.get_text(strip=True) if span else ""
                # Common name is the label text minus the span text
                full_text = label.get_text(strip=True)
                name = full_text.removesuffix(scientific_name).strip()
            else:
                name = a_tag.get_text(strip=True)
                scientific_name = ""

            result[key].append(
                {"slug": slug, "name": name, "scientific_name": scientific_name}
            )

    return result


def scrape_plant_relationships(
    client: httpx.Client,
    plant: dict,
    delay: float = REQUEST_DELAY,
) -> dict | None:
    link = plant.get("link")
    if not link:
        return None

    url = f"{SITE_URL}{link}"
    logger.debug("GET %s", url)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.get(url, timeout=30.0)
            response.raise_for_status()
            break
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

    relationships = parse_relationships(response.text)

    return {
        "id": plant.get("id"),
        "name": plant.get("name"),
        "slug": plant.get("slug"),
        "companions": relationships["companions"],
        "antagonists": relationships["antagonists"],
    }
