from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import DEFAULT_KEYWORDS
from storage import get_seen_links, mark_links_seen


@dataclass
class Order:
    title: str
    url: str
    snippet: str
    source: str


async def fetch_html(url: str, timeout: int = 15) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


def _match_keywords(text: str, keywords: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords)


def _extract_orders_kwork(html: str, base_url: str, keywords: Sequence[str]) -> List[Order]:
    """
    Специализированный парсер kwork.ru (страницы проектов).
    Структура может меняться, поэтому при ошибке есть запасной универсальный парсер.
    """
    soup = BeautifulSoup(html, "html.parser")
    orders: List[Order] = []

    # Карточки заказов
    cards = soup.select("div.wants-card")
    for card in cards:
        title_tag = card.select_one("a.wants-card__header-title, a.js-want-block-toggle")
        if not title_tag or not title_tag.get("href"):
            continue

        title = " ".join(title_tag.stripped_strings)
        href = title_tag["href"]
        full_url = urljoin(base_url, href)

        desc_tag = card.select_one("div.wants-card__description, div.breakwords")
        desc = " ".join(desc_tag.stripped_strings) if desc_tag else title

        text_for_match = f"{title} {desc}"
        if not _match_keywords(text_for_match, keywords):
            continue

        orders.append(
            Order(
                title=title[:200] or "Новый заказ на Kwork",
                url=full_url,
                snippet=desc[:400],
                source="kwork.ru",
            )
        )

    return orders


def _extract_orders_fl(html: str, base_url: str, keywords: Sequence[str]) -> List[Order]:
    """
    Специализированный парсер fl.ru (страница проектов).
    """
    soup = BeautifulSoup(html, "html.parser")
    orders: List[Order] = []

    # Основные блоки проектов
    posts = soup.select("div.b-post")
    for post in posts:
        title_tag = post.select_one("a.b-post__link")
        if not title_tag or not title_tag.get("href"):
            continue

        title = " ".join(title_tag.stripped_strings)
        href = title_tag["href"]
        full_url = urljoin(base_url, href)

        desc_tag = post.select_one("div.b-post__body, div.b-post__txt")
        desc = " ".join(desc_tag.stripped_strings) if desc_tag else title

        text_for_match = f"{title} {desc}"
        if not _match_keywords(text_for_match, keywords):
            continue

        orders.append(
            Order(
                title=title[:200] or "Новый заказ на fl.ru",
                url=full_url,
                snippet=desc[:400],
                source="fl.ru",
            )
        )

    return orders


def _extract_orders_generic(html: str, base_url: str, keywords: Sequence[str]) -> List[Order]:
    """
    Универсальный грубый парсер:
    - находит все <a>
    - если текст ссылки или ближайшего контейнера содержит ключевое слово — считаем это заказом
    """
    soup = BeautifulSoup(html, "html.parser")
    orders: List[Order] = []

    for a in soup.find_all("a", href=True):
        text = " ".join(a.stripped_strings)
        if not text:
            continue

        # небольшой контекст вокруг ссылки
        parent_text = " ".join(a.parent.stripped_strings) if a.parent else text

        candidate_text = f"{text} {parent_text}"
        if not _match_keywords(candidate_text, keywords):
            continue

        href = a["href"]
        full_url = urljoin(base_url, href)

        title = text[:200]
        snippet = parent_text[:400]

        orders.append(
            Order(
                title=title or "Новый заказ",
                url=full_url,
                snippet=snippet,
                source=base_url,
            )
        )

    # убираем дубликаты по ссылке
    unique: dict[str, Order] = {}
    for o in orders:
        unique[o.url] = o
    return list(unique.values())


async def find_new_orders_for_site(site_url: str, keywords: Iterable[str] | None = None) -> List[Order]:
    html = await fetch_html(site_url)
    if not html:
        return []

    kws = list(keywords) if keywords else DEFAULT_KEYWORDS
    parsed = urlparse(site_url)
    hostname = (parsed.hostname or "").lower()

    if "kwork.ru" in hostname:
        specific = _extract_orders_kwork(html, site_url, kws)
        if specific:
            all_orders = specific
        else:
            all_orders = _extract_orders_generic(html, site_url, kws)
    elif hostname.endswith("fl.ru"):
        specific = _extract_orders_fl(html, site_url, kws)
        if specific:
            all_orders = specific
        else:
            all_orders = _extract_orders_generic(html, site_url, kws)
    else:
        all_orders = _extract_orders_generic(html, site_url, kws)

    seen = get_seen_links()
    seen_for_site = set(seen.get(site_url, []))

    new_orders = [o for o in all_orders if o.url not in seen_for_site]
    if new_orders:
        mark_links_seen(site_url, {o.url for o in new_orders})

    return new_orders


async def find_new_orders_for_all_sites(sites: Sequence[str], keywords: Iterable[str] | None = None) -> List[Order]:
    all_new: List[Order] = []
    for site in sites:
        orders = await find_new_orders_for_site(site, keywords=keywords)
        all_new.extend(orders)
    return all_new

