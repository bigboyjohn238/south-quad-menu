"""Retrieve the verified public South Quad menu and publish Markdown, JSON, HTML."""
from __future__ import annotations
from collections import OrderedDict
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import json
import re
from bs4 import BeautifulSoup, Tag

SOURCE = "https://dining.umich.edu/menus-locations/dining-halls/south-quad/"
DOCS = Path(__file__).resolve().parent / "docs"
TZ = ZoneInfo("America/Detroit")

def clean(s):
    return " ".join(str(s).split())

def nutrition_of(item):
    panel = item.find("div", class_="nutrition")
    if panel is None:
        panel = item.find_next_sibling("div", class_="nutrition")
    if panel is None:
        return {}
    table = panel.select_one("table.nutrition-facts")
    if table is None:
        return {}
    result = {}
    for selector, name in [(".serving-size", "Serving Size"), (".portion-calories", "Calories")]:
        tag = table.select_one(selector)
        if tag:
            result[name] = clean(tag.get_text(" ", strip=True)).removeprefix(name).strip()
    for tr in table.select("tr"):
        cls = tr.get("class", [])
        if any(c in cls for c in ("nutrition-facts-header", "serving-size", "portion-calories")):
            continue
        cells = tr.find_all("td", recursive=False)
        if cells:
            label = clean(cells[0].get_text(" ", strip=True))
            if label and not label.startswith(("Amount Per Serving", "% Daily Value")):
                result[label] = clean(cells[1].get_text(" ", strip=True)) if len(cells) > 1 else ""
    return result

def parse_menu_html(html, menu_date):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("#mdining-items")
    if root is None:
        raise ValueError("No #mdining-items element; menu content may be blocked or absent")
    text = clean(soup.get_text(" ", strip=True))
    match = re.search(
        r"Menu for\\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\\s+"
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\\s+\\d{1,2},\\s+\\d{4})", text, flags=re.I)
    if not match:
        raise ValueError("Unable to verify displayed menu date; refusing possibly stale food data")
    shown_date = datetime.strptime(match.group(1), "%A, %B %d, %Y").date().isoformat()
    if shown_date != menu_date:
        raise ValueError(f"Wrong menu date: expected {menu_date}, displayed {shown_date}")
    meals = OrderedDict()
    for heading in root.find_all("h3", recursive=False):
        meal = clean(heading.get_text(" ", strip=True))
        section = heading.find_next_sibling()
        if not meal or section is None:
            continue
        entries = []
        for category in section.select("ul.courses_wrapper > li"):
            header = category.find("h4", recursive=False)
            station = clean(header.get_text(" ", strip=True)) if header else "Other"
            for item in category.select("ul.items > li"):
                name_tag = item.select_one(".item-name")
                if name_tag is None:
                    continue
                clone = BeautifulSoup(str(name_tag), "html.parser")
                for price in clone.select(".price"):
                    price.decompose()
                name = clean(clone.get_text(" ", strip=True))
                if not name:
                    continue
                classes = item.get("class", [])
                entries.append({
                    "name": name, "station": station,
                    "allergens": [c.removeprefix("allergen-") for c in classes if c.startswith("allergen-")],
                    "traits": [c.removeprefix("trait-") for c in classes if c.startswith("trait-")],
                    "nutrition": nutrition_of(item),
                })
        if entries:
            meals[meal] = entries
    if not meals:
        raise ValueError("No verified item-level menu; will not publish a fabricated or empty menu")
    return {
        "date": menu_date,
        "dining_hall": "South Quad",
        "source": SOURCE + "?menuDate=" + menu_date,
        "retrieved_at": datetime.now(TZ).isoformat(),
        "meals": meals
    }

def fetch_html(menu_date):
    from playwright.sync_api import sync_playwright
    url = SOURCE + "?menuDate=" + menu_date
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                locale="en-US", timezone_id="America/Detroit",
                user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"))
            page = context.new_page()
            failure = ""
            for attempt in range(3):
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    if response is None or response.status != 200:
                        raise RuntimeError(f"HTTP {response.status if response else 'no response'}")
                    page.locator("#mdining-items").wait_for(timeout=20000)
                    html = page.content()
                    parse_menu_html(html, menu_date)
                    return html
                except Exception as e:
                    failure = str(e)
                    print(f"Attempt {attempt+1} failed: {failure}", flush=True)
                    if attempt != 2:
                        page.wait_for_timeout(3000 * (attempt + 1))
            raise RuntimeError(f"Three menu attempts failed: {failure}")
        finally:
            browser.close()

def make_markdown(data):
    parts = [f"# South Quad menu — {data['date']}", "",
             f"Source: {data['source']}", f"Retrieved: {data['retrieved_at']}", "",
             "Dishes are published offerings, not guaranteed inventory. Allergens must be confirmed with dining staff.", ""]
    for meal, items in data["meals"].items():
        parts += [f"## {meal} ({len(items)} items)", ""]
        by_station = OrderedDict()
        for food in items:
            by_station.setdefault(food["station"], []).append(food)
        for station, foods in by_station.items():
            parts.append(f"### {station}")
            for food in foods:
                facts = food["nutrition"]
                macros = "; ".join(f"{k}: {v}" for k, v in facts.items() if
                                   k in ("Serving Size", "Calories") or
                                   re.search(r"protein|carbohydrate|fiber|fat|sodium", k, re.I))
                notes = []
                if food["allergens"]:
                    notes.append("listed allergens: " + ", ".join(food["allergens"]))
                if macros:
                    notes.append(macros)
                parts.append("- " + food["name"] + (" — " + " | ".join(notes) if notes else ""))
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"

def make_html(data):
    parts = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
             "<meta name='viewport' content='width=device-width,initial-scale=1'>",
             "<title>South Quad Daily Menu</title></head><body>",
             f"<h1>South Quad menu — {escape(data['date'])}</h1>",
             f"<p>Source: <a href='{escape(data['source'])}'>Michigan Dining</a>; retrieved {escape(data['retrieved_at'])}</p>",
             "<p>Confirm availability and allergies directly with dining staff.</p>"]
    for meal, items in data["meals"].items():
        parts.append(f"<h2>{escape(meal)}</h2><ul>")
        for food in items:
            parts.append(f"<li>{escape(food['name'])} ({escape(food['station'])})</li>")
        parts.append("</ul>")
    parts.append("</body></html>")
    return "\n".join(parts)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD, default today in Ann Arbor")
    args = p.parse_args()
    date = args.date or datetime.now(TZ).date().isoformat()
    datetime.strptime(date, "%Y-%m-%d")
    data = parse_menu_html(fetch_html(date), date)
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "today.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOCS / "today.md").write_text(make_markdown(data), encoding="utf-8")
    (DOCS / "index.html").write_text(make_html(data), encoding="utf-8")
    print(f"Published {sum(map(len, data['meals'].values()))} dishes for {date} across {list(data['meals'])}")

if __name__ == "__main__":
    main()
