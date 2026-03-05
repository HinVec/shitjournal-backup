#!/usr/bin/env python3
"""
S.H.I.T Journal 文章爬虫 — 从 shitjournal.org 抓取新闻与预印本并备份为 Markdown。
站点为 SPA，使用 Playwright 渲染后解析。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import typer
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tqdm import tqdm

BASE_URL = "https://shitjournal.org"
OUTPUT_DIR = Path(__file__).resolve().parent / "backup"
DELAY_SECONDS = 1.0  # 礼貌爬取间隔


def slugify(s: str) -> str:
    """生成安全的文件名 slug。"""
    s = re.sub(r"[^\w\s\-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:80] or "untitled"


def extract_news_links_from_page(page) -> list[str]:
    """从当前新闻列表页获取所有新闻详情页 URL。"""
    links = page.eval_on_selector_all(
        'a[href*="/news/"]',
        """els => {
        const set = new Set();
        for (const e of els) {
            const h = e.getAttribute('href') || '';
            if (h.startsWith('/news/') && h !== '/news' && h !== '/news/') {
                set.add(new URL(e.href).href);
            }
        }
        return Array.from(set);
    }""",
    )
    return list(links) if links else []


def extract_article_content(soup: BeautifulSoup) -> dict:
    """
    从文章页 HTML 提取：标题、副标题、正文。
    返回 {"title", "subtitle", "body_html", "body_text"}。
    """
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"content|article|post", re.I))
        or soup.find("body")
    )
    if not main:
        main = soup

    title_el = main.find("h1") or soup.find("h1")
    title = (title_el.get_text(strip=True) if title_el else "") or "Untitled"

    subtitle = ""
    next_el = title_el.next_sibling if title_el else None
    for _ in range(10):
        if next_el is None:
            break
        if isinstance(next_el, str):
            t = next_el.strip()
            if t and len(t) < 200:
                subtitle = t
                break
        elif getattr(next_el, "name", None) and next_el.name in ("p", "div", "span"):
            subtitle = next_el.get_text(strip=True)[:200]
            break
        next_el = getattr(next_el, "next_sibling", None)

    body_html = ""
    if main:
        for tag in main.find_all(["script", "style", "nav", "header"]):
            tag.decompose()
        body_html = main.decode_contents() if main else ""

    body_text = BeautifulSoup(body_html, "html.parser").get_text(separator="\n", strip=True)
    body_text = re.sub(r"\n{3,}", "\n\n", body_text)

    return {
        "title": title,
        "subtitle": subtitle,
        "body_html": body_html,
        "body_text": body_text,
    }


def html_to_simple_markdown(html: str) -> str:
    """将正文 HTML 转为简易 Markdown。"""
    soup = BeautifulSoup(html, "html.parser")
    parts = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "a"]):
        text = el.get_text(strip=True)
        if not text:
            continue
        if el.name == "h1":
            parts.append(f"\n# {text}\n")
        elif el.name == "h2":
            parts.append(f"\n## {text}\n")
        elif el.name == "h3":
            parts.append(f"\n### {text}\n")
        elif el.name == "h4":
            parts.append(f"\n#### {text}\n")
        elif el.name in ("h5", "h6"):
            parts.append(f"\n##### {text}\n")
        elif el.name == "a" and el.get("href"):
            parts.append(f"[{text}]({el['href']})")
        elif el.name == "li":
            parts.append(f"- {text}")
        else:
            parts.append(f"\n{text}\n")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(parts).strip())


def save_article(data: dict, subdir: str) -> Path | None:
    """将文章保存为 Markdown 和 JSON 元数据。"""
    subpath = OUTPUT_DIR / subdir
    subpath.mkdir(parents=True, exist_ok=True)
    slug = data.get("slug") or slugify(data.get("title", "untitled"))
    safe_slug = slugify(slug) or "untitled"

    md_content = f"""# {data.get('title', 'Untitled')}

- **URL**: {data.get('url', '')}
- **Subtitle**: {data.get('subtitle', '')}

---

{html_to_simple_markdown(data.get('body_html', ''))}
"""
    md_path = subpath / f"{safe_slug}.md"
    md_path.write_text(md_content, encoding="utf-8")

    meta_path = subpath / f"{safe_slug}.meta.json"
    meta = {k: v for k, v in data.items() if k != "body_html"}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return md_path


def run_crawl(
    output_dir: Path | None = None,
    news_only: bool = False,
    delay: float = DELAY_SECONDS,
    headless: bool = True,
) -> None:
    """执行抓取：用 Playwright 打开新闻列表与各文章页，解析并保存。"""
    global OUTPUT_DIR
    OUTPUT_DIR = Path(output_dir or OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = {
        "news": [],
        "preprints": [],
        "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="ShitJournalBackup/1.0 (+https://github.com; backup bot)",
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()
        page.set_default_timeout(20000)

        # 1) 新闻列表
        page.goto(f"{BASE_URL}/news", wait_until="networkidle")
        time.sleep(0.5)
        news_urls = extract_news_links_from_page(page)
        typer.echo(f"发现 {len(news_urls)} 篇新闻。")

        for url in tqdm(news_urls, desc="新闻"):
            time.sleep(delay)
            page.goto(url, wait_until="networkidle")
            time.sleep(0.3)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            data = extract_article_content(soup)
            data["url"] = url
            data["slug"] = url.rstrip("/").split("/")[-1] or "index"
            save_article(data, "news")
            index["news"].append({"url": url, "slug": data.get("slug"), "title": data.get("title")})

        # 2) 预印本（列表页上的详情链接）
        if not news_only:
            page.goto(f"{BASE_URL}/preprints", wait_until="networkidle")
            time.sleep(0.5)
            preprint_links = page.eval_on_selector_all(
                'a[href*="/preprints/"]',
                """els => {
                const set = new Set();
                for (const e of els) {
                    const h = (e.getAttribute('href') || '').split('?')[0];
                    if (/^\\/preprints\\/[^/]+\\/?$/.test(h)) set.add(new URL(e.href).href);
                }
                return Array.from(set);
            }""",
            )
            preprint_urls = list(preprint_links) if preprint_links else []
            for url in tqdm(preprint_urls, desc="预印本"):
                time.sleep(delay)
                page.goto(url, wait_until="networkidle")
                time.sleep(0.3)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                data = extract_article_content(soup)
                data["url"] = url
                data["slug"] = url.rstrip("/").split("/")[-1] or "index"
                save_article(data, "preprints")
                index["preprints"].append({"url": url, "slug": data.get("slug"), "title": data.get("title")})

        context.close()
        browser.close()

    index_path = OUTPUT_DIR / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"索引已写入: {index_path}")


app = typer.Typer(help="S.H.I.T Journal 备份爬虫")


@app.command("crawl")
def crawl_cmd(
    output_dir: Path = typer.Option(OUTPUT_DIR, "--output", "-o", help="备份输出目录"),
    news_only: bool = typer.Option(False, "--news-only", help="仅抓取新闻"),
    delay: float = typer.Option(DELAY_SECONDS, "--delay", help="请求间隔秒数"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="是否无头模式"),
) -> None:
    """抓取 shitjournal.org 新闻与预印本并保存为 Markdown。"""
    run_crawl(output_dir=output_dir, news_only=news_only, delay=delay, headless=headless)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run_crawl()


if __name__ == "__main__":
    app()
