"""Перевірка каталогу Listening: python scripts/validate_catalog.py [--check-urls]"""
import json
import sys
import urllib.request
from urllib.parse import urlparse

REQUIRED = ["resource_id", "title", "provider", "url", "level", "topics", "exercise_type",
            "estimated_minutes", "ielts_relevance", "answer_key_available", "status"]
CEFR = ["A1", "A2", "B1", "B2", "C1", "C2"]


def main(path="data/listening_resources.json", check_urls=False) -> int:
    items, errors, seen = json.load(open(path, encoding="utf-8")), [], set()
    for r in items:
        rid = r.get("resource_id", "?")
        errors += [f"{rid}: відсутнє поле {k}" for k in REQUIRED if k not in r]
        if rid in seen:
            errors.append(f"{rid}: дубль resource_id")
        seen.add(rid)
        u = urlparse(r.get("url", ""))
        if u.scheme != "https" or not u.netloc:
            errors.append(f"{rid}: URL має бути https")
        lo, _, hi = r.get("level", "").partition("-")
        if lo not in CEFR or (hi and hi not in CEFR):
            errors.append(f"{rid}: некоректний level")
        if check_urls and u.scheme == "https":
            try:
                req = urllib.request.Request(r["url"], method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
                urllib.request.urlopen(req, timeout=10)
            except Exception as e:  # noqa
                errors.append(f"{rid}: URL недоступний ({e})")
    print("\n".join(errors) or f"OK: {len(items)} ресурсів")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(check_urls="--check-urls" in sys.argv))
