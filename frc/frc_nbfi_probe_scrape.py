"""
FRC NBFI scraper - probe first, then scrape.

Target:
- FRC regulated organization list for NBFI sector id=12
- Extract organization name, register, activity/license/status fields from detail pages when available.

Run:
    pip install pandas playwright beautifulsoup4 lxml openpyxl
    playwright install chromium
    python frc_nbfi_probe_scrape.py

Outputs:
    outputs/frc_network_probe.csv
    outputs/frc_visible_rows.csv
    outputs/frc_nbfi_register_raw.csv
    outputs/frc_nbfi_register_clean.csv
    outputs/frc_scrape_quality_report.csv
    outputs/debug_frc_nbfi.html
    outputs/debug_frc_nbfi.png
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Response


START_URL = "https://www.frc.mn/#/sct;id=12/org"
OUT_DIR = Path("outputs")
OUT_DIR.mkdir(exist_ok=True)

HEADLESS = False          # first run: False, structure харахад амар
MAX_DETAIL_PAGES = 800    # safety limit
SCROLL_ROUNDS = 80
WAIT_MS = 800


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_name(value: str) -> str:
    value = clean_text(value).upper()
    for token in [
        "ББСБ", "БАНК БУС САНХҮҮГИЙН БАЙГУУЛЛАГА",
        "ХХК", "ХК", "LLC", "JSC", "КОМПАНИ"
    ]:
        value = value.replace(token, "")
    value = re.sub(r"[^\wА-ЯӨҮЁа-яөүё0-9]+", "", value)
    return value


def extract_register(text: str) -> str:
    """
    Mongolian company register is usually 7 digits.
    Detail page дээр 'Регистр', 'Улсын бүртгэлийн дугаар' гэх label-ийн ойролцоо гарна.
    """
    text = clean_text(text)
    candidates = re.findall(r"\b\d{7}\b", text)
    return candidates[0] if candidates else ""


def flatten_json(obj: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten_json(v, key))
    elif isinstance(obj, list):
        out[prefix or "list_len"] = f"[list:{len(obj)}]"
    else:
        out[prefix] = obj
    return out


def find_records_in_json(obj: Any) -> list[dict[str, Any]]:
    """
    API endpoint олдвол JSON дотроос байгууллага шиг record-уудыг хайна.
    register/name/title/activity/status гэх түлхүүр орсон dict-үүдийг record гэж үзнэ.
    """
    records: list[dict[str, Any]] = []

    def walk(x: Any):
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x.keys()}
            looks_like_org = any(
                token in " ".join(keys)
                for token in ["register", "reg", "name", "title", "org", "company", "activity", "license"]
            )
            if looks_like_org and len(x) >= 2:
                flat = flatten_json(x)
                text_blob = " ".join(clean_text(v) for v in flat.values())
                if ("Банк бус" in text_blob or "ББСБ" in text_blob or extract_register(text_blob)):
                    records.append(flat)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)
    return records


async def collect_network_response(response: Response, bucket: list[dict[str, Any]]) -> None:
    url = response.url
    ctype = response.headers.get("content-type", "")
    if not any(x in ctype.lower() for x in ["json", "javascript"]) and not any(
        x in url.lower() for x in ["api", "org", "sct", "license", "special", "company"]
    ):
        return

    item = {
        "url": url,
        "status": response.status,
        "content_type": ctype,
        "method": response.request.method,
        "resource_type": response.request.resource_type,
        "record_count_guess": 0,
        "sample_keys": "",
        "error": "",
    }

    try:
        text = await response.text()
        item["body_size"] = len(text)

        if "json" in ctype.lower() or text[:1] in ["{", "["]:
            data = json.loads(text)
            records = find_records_in_json(data)
            item["record_count_guess"] = len(records)
            if records:
                item["sample_keys"] = ", ".join(list(records[0].keys())[:25])
                probe_json_path = OUT_DIR / "frc_api_records_guess.jsonl"
                with probe_json_path.open("a", encoding="utf-8") as f:
                    for rec in records:
                        rec["_source_url"] = url
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        item["error"] = str(e)[:300]

    bucket.append(item)


async def save_debug_artifacts(page: Page) -> None:
    html = await page.content()
    (OUT_DIR / "debug_frc_nbfi.html").write_text(html, encoding="utf-8")
    await page.screenshot(path=str(OUT_DIR / "debug_frc_nbfi.png"), full_page=True)


async def scroll_to_load(page: Page) -> None:
    previous_height = 0
    same_count = 0

    for _ in range(SCROLL_ROUNDS):
        await page.mouse.wheel(0, 2500)
        await page.wait_for_timeout(WAIT_MS)

        height = await page.evaluate("document.body.scrollHeight")
        if height == previous_height:
            same_count += 1
        else:
            same_count = 0

        previous_height = height
        if same_count >= 5:
            break


async def extract_visible_rows(page: Page) -> pd.DataFrame:
    """
    DOM дээр харагдаж байгаа list/card/table row-уудыг generic байдлаар авна.
    API endpoint олдохгүй үед structure шалгах fallback.
    """
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    candidates = []
    selectors = ["tr", ".card", ".list-group-item", "mat-row", "[role='row']", "li", "a"]
    for sel in selectors:
        for el in soup.select(sel):
            text = clean_text(el.get_text(" ", strip=True))
            href = ""
            if el.name == "a":
                href = el.get("href") or ""
            else:
                a = el.select_one("a[href]")
                href = a.get("href") if a else ""

            if len(text) < 5:
                continue
            if "Банк бус" not in text and "ББСБ" not in text and not extract_register(text):
                continue

            candidates.append({
                "text": text,
                "register_guess": extract_register(text),
                "href": href,
                "text_len": len(text),
            })

    df = pd.DataFrame(candidates).drop_duplicates()
    if not df.empty:
        df.to_csv(OUT_DIR / "frc_visible_rows.csv", index=False, encoding="utf-8-sig")
    return df


async def get_clickable_detail_candidates(page: Page) -> list[dict[str, str]]:
    """
    Rows/cards/links дотроос detail рүү орох боломжтой element-үүдийг олно.
    """
    candidates = await page.locator("a, button, tr, .card, .list-group-item, [role='row']").evaluate_all(
        """els => els.map((el, idx) => ({
            idx,
            text: (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim(),
            href: el.href || el.getAttribute('href') || '',
            tag: el.tagName
        })).filter(x => x.text.length > 3)"""
    )

    filtered = []
    seen = set()
    for c in candidates:
        text = clean_text(c.get("text", ""))
        href = clean_text(c.get("href", ""))
        key = (text[:120], href)
        if key in seen:
            continue
        seen.add(key)

        if "Банк бус" in text or "ББСБ" in text or extract_register(text) or href:
            filtered.append({"text": text, "href": href, "tag": c.get("tag", ""), "idx": str(c.get("idx", ""))})
    return filtered[:MAX_DETAIL_PAGES]


async def parse_detail_page(page: Page, source_url: str = "") -> dict[str, Any]:
    text = clean_text(await page.locator("body").inner_text())
    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    # label:value хэлбэрийн мөрүүдийг хадгална
    rows = []
    for el in soup.select("tr, p, div, li"):
        t = clean_text(el.get_text(" ", strip=True))
        if any(k in t.lower() for k in ["регистр", "register", "байгууллага", "зөвшөөрөл", "үйл ажиллагаа", "хаяг", "утас"]):
            if 3 <= len(t) <= 400:
                rows.append(t)

    company_name = ""
    # first h1/h2/h3/title-like text
    for sel in ["h1", "h2", "h3", ".title", ".name"]:
        node = soup.select_one(sel)
        if node:
            company_name = clean_text(node.get_text(" ", strip=True))
            if company_name:
                break

    if not company_name:
        # fallback: first meaningful line
        for line in text.split(" "):
            pass
        company_name = clean_text(text[:120])

    return {
        "register": extract_register(text),
        "company_name": company_name,
        "nbfi_join_key": normalize_name(company_name),
        "page_text": text[:3000],
        "detail_rows": " | ".join(rows[:30]),
        "source_detail_url": source_url or page.url,
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
    }


async def scrape_by_clicking_details(page: Page) -> pd.DataFrame:
    """
    API-гүй бол visible list дээрх clickable мөрүүдийг дараад detail мэдээлэл унших оролдлого.
    FRC SPA selector өөрчлөгдвөл энэ хэсгийг тухайн DOM-д тааруулж засна.
    """
    candidates = await get_clickable_detail_candidates(page)
    records = []

    for i, cand in enumerate(candidates, start=1):
        try:
            before_url = page.url

            if cand["href"] and cand["href"].startswith("http"):
                detail = await page.context.new_page()
                await detail.goto(cand["href"], wait_until="networkidle", timeout=60000)
                await detail.wait_for_timeout(1000)
                rec = await parse_detail_page(detail, cand["href"])
                await detail.close()
            else:
                locator = page.locator("a, button, tr, .card, .list-group-item, [role='row']").nth(int(cand["idx"]))
                await locator.click(timeout=5000)
                await page.wait_for_load_state("networkidle", timeout=20000)
                await page.wait_for_timeout(1000)
                rec = await parse_detail_page(page, page.url)

                # Back to list
                if page.url != before_url:
                    await page.go_back(wait_until="networkidle", timeout=30000)
                else:
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)

            rec["list_text"] = cand["text"]
            records.append(rec)

            if i % 25 == 0:
                print(f"detail scraped: {i}/{len(candidates)}")

        except Exception as e:
            records.append({
                "register": "",
                "company_name": "",
                "nbfi_join_key": "",
                "page_text": "",
                "detail_rows": "",
                "source_detail_url": cand.get("href", ""),
                "list_text": cand.get("text", ""),
                "error": str(e)[:300],
                "scraped_at": datetime.now().isoformat(timespec="seconds"),
            })

    df = pd.DataFrame(records)
    if not df.empty:
        df.to_csv(OUT_DIR / "frc_nbfi_register_raw.csv", index=False, encoding="utf-8-sig")
    return df


def clean_final(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return raw_df

    df = raw_df.copy()
    for col in ["register", "company_name", "nbfi_join_key"]:
        if col not in df.columns:
            df[col] = ""

    # Detail page нэр хоосон бол list_text-ээс fallback авах
    if "list_text" in df.columns:
        mask = df["company_name"].fillna("").str.len() < 3
        df.loc[mask, "company_name"] = df.loc[mask, "list_text"].fillna("").str[:160]

    df["company_name"] = df["company_name"].map(clean_text)
    df["register"] = df["register"].map(clean_text)
    df["nbfi_join_key"] = df["company_name"].map(normalize_name)

    # register байвал register-р, үгүй бол name-р dedupe
    df["dedupe_key"] = df.apply(
        lambda r: r["register"] if r["register"] else r["nbfi_join_key"],
        axis=1
    )

    df = df[df["dedupe_key"].astype(str).str.len() > 0].copy()
    df = df.drop_duplicates(subset=["dedupe_key"], keep="first")

    keep_cols = [
        "register", "company_name", "nbfi_join_key",
        "detail_rows", "source_detail_url", "scraped_at"
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = ""

    return df[keep_cols].sort_values(["company_name", "register"])


def build_quality_report(network_df: pd.DataFrame, visible_df: pd.DataFrame, final_df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"check_name": "network_responses_captured", "value": len(network_df), "status": "info"},
        {"check_name": "visible_rows_captured", "value": len(visible_df), "status": "info"},
        {"check_name": "final_rows", "value": len(final_df), "status": "info"},
        {
            "check_name": "distinct_register_count",
            "value": final_df["register"].replace("", pd.NA).dropna().nunique() if not final_df.empty else 0,
            "status": "info"
        },
        {
            "check_name": "missing_register_count",
            "value": int((final_df["register"].fillna("") == "").sum()) if not final_df.empty else 0,
            "status": "warning"
        },
        {
            "check_name": "duplicate_register_count",
            "value": int(final_df["register"].replace("", pd.NA).dropna().duplicated().sum()) if not final_df.empty else 0,
            "status": "warning"
        },
    ]
    return pd.DataFrame(rows)


async def main() -> None:
    network_bucket: list[dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            locale="mn-MN",
            viewport={"width": 1440, "height": 1200},
        )
        page = await context.new_page()
        page.on("response", lambda response: asyncio.create_task(collect_network_response(response, network_bucket)))

        print(f"Opening: {START_URL}")
        await page.goto(START_URL, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(3000)

        await scroll_to_load(page)
        await save_debug_artifacts(page)

        visible_df = await extract_visible_rows(page)

        # Save network probe
        network_df = pd.DataFrame(network_bucket).drop_duplicates()
        if not network_df.empty:
            network_df.to_csv(OUT_DIR / "frc_network_probe.csv", index=False, encoding="utf-8-sig")
            print("Network probe saved:", OUT_DIR / "frc_network_probe.csv")

        # If API records were discovered, use them first
        api_jsonl = OUT_DIR / "frc_api_records_guess.jsonl"
        api_records = []
        if api_jsonl.exists():
            with api_jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        api_records.append(json.loads(line))
                    except Exception:
                        pass

        if api_records:
            api_df = pd.DataFrame(api_records)
            # Generic rename guesses
            rename_map = {}
            for c in api_df.columns:
                cl = c.lower()
                if "register" in cl or cl.endswith(".reg") or "regno" in cl:
                    rename_map[c] = "register"
                elif "name" in cl or "title" in cl:
                    if "company_name" not in rename_map.values():
                        rename_map[c] = "company_name"
            raw_df = api_df.rename(columns=rename_map)
            if "source_detail_url" not in raw_df.columns and "_source_url" in raw_df.columns:
                raw_df["source_detail_url"] = raw_df["_source_url"]
            raw_df.to_csv(OUT_DIR / "frc_nbfi_register_raw.csv", index=False, encoding="utf-8-sig")
        else:
            print("No obvious API records found. Trying DOM/detail click fallback...")
            raw_df = await scrape_by_clicking_details(page)

        await browser.close()

    final_df = clean_final(raw_df)
    final_df.to_csv(OUT_DIR / "frc_nbfi_register_clean.csv", index=False, encoding="utf-8-sig")

    quality_df = build_quality_report(network_df, visible_df, final_df)
    quality_df.to_csv(OUT_DIR / "frc_scrape_quality_report.csv", index=False, encoding="utf-8-sig")

    print("\nDone.")
    print("Final rows:", len(final_df))
    print("Distinct register:", final_df["register"].replace("", pd.NA).dropna().nunique() if not final_df.empty else 0)
    print("Missing register:", int((final_df["register"].fillna("") == "").sum()) if not final_df.empty else 0)
    print("Outputs:")
    for path in [
        "frc_network_probe.csv",
        "frc_visible_rows.csv",
        "frc_nbfi_register_raw.csv",
        "frc_nbfi_register_clean.csv",
        "frc_scrape_quality_report.csv",
        "debug_frc_nbfi.html",
        "debug_frc_nbfi.png",
    ]:
        print(" -", OUT_DIR / path)


if __name__ == "__main__":
    asyncio.run(main())
