import json
from pathlib import Path
from typing import Dict, List, Set


BASE_DIR = Path(__file__).parent
SITES_FILE = BASE_DIR / "sites.json"
SEEN_FILE = BASE_DIR / "seen_links.json"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_sites() -> List[str]:
    data = _read_json(SITES_FILE, [])
    return list(dict.fromkeys(data))  # убираем дубликаты, сохраняем порядок


def add_site(url: str) -> bool:
    url = url.strip()
    if not url:
        return False
    sites = get_sites()
    if url in sites:
        return False
    sites.append(url)
    _write_json(SITES_FILE, sites)
    return True


def remove_site(url: str) -> bool:
    sites = get_sites()
    if url not in sites:
        return False
    sites = [s for s in sites if s != url]
    _write_json(SITES_FILE, sites)
    return True


def get_seen_links() -> Dict[str, List[str]]:
    return _read_json(SEEN_FILE, {})


def mark_links_seen(site: str, links: Set[str]) -> None:
    data = get_seen_links()
    site_links = set(data.get(site, []))
    site_links.update(links)
    data[site] = sorted(site_links)
    _write_json(SEEN_FILE, data)
