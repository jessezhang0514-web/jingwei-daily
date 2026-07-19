#!/usr/bin/env python3
"""Render the latest digest into index.html as a no-JavaScript fallback."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
DATA = ROOT / "docs" / "data" / "digests.json"

FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=900&q=80",
]


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def safe_url(value: object) -> str:
    value = str(value or "")
    parsed = urlparse(value)
    return esc(value) if parsed.scheme in {"http", "https"} else ""


def replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not update index.html pattern: {pattern}")
    return updated


def card(article: dict, position: int) -> str:
    image = safe_url(article.get("imageUrl")) or FALLBACK_IMAGES[position % len(FALLBACK_IMAGES)]
    source_url = safe_url(article.get("sourceUrl"))
    rank = int(article.get("rank") or position + 1)
    lead = " lead" if position == 0 else ""
    credit = f"图片：{esc(article.get('imageCredit'))}" if article.get("imageCredit") else ""
    return (
        f'<article class="card{lead}"><a class="pic" href="{source_url}" target="_blank" rel="noreferrer">'
        f'<img src="{image}" alt="{esc(article.get("title"))}"><span class="rank">{rank:02d}</span>'
        f'<span class="cat">{esc(article.get("category"))}</span></a><div class="body"><div class="source">'
        f'<span>{esc(article.get("source"))}</span><span>{esc(article.get("eventTime"))}</span></div>'
        f'<h3><a href="{source_url}" target="_blank" rel="noreferrer">{esc(article.get("title"))}</a></h3>'
        f'<p>{esc(article.get("summary"))}</p><div class="why"><strong>为什么重要</strong>'
        f'{esc(article.get("whyImportant"))}</div><div class="foot"><a href="{source_url}" target="_blank" '
        f'rel="noreferrer">阅读原文 ↗</a><span>{credit}</span></div></div></article>'
    )


def main() -> None:
    digests = json.loads(DATA.read_text(encoding="utf-8"))
    if not digests:
        raise RuntimeError("digests.json is empty")
    digest = sorted(digests, key=lambda item: str(item.get("date", "")), reverse=True)[0]
    articles = sorted(digest.get("articles", []), key=lambda item: int(item.get("rank", 999)))
    if len(articles) != 20:
        raise RuntimeError(f"Expected 20 articles, found {len(articles)}")

    text = INDEX.read_text(encoding="utf-8")
    text = replace_once(text, r'<h1 id="title">.*?</h1>', f'<h1 id="title">{esc(digest.get("title"))}</h1>')
    text = replace_once(text, r'<span id="date">.*?</span>', f'<span id="date">{esc(digest.get("date"))}</span>')
    text = replace_once(text, r'<span id="count">.*?</span>', '<span id="count">20 则新闻</span>')
    text = replace_once(
        text,
        r'<span id="updated">.*?</span>',
        f'<span id="updated">更新于 {esc(digest.get("generatedAt"))}</span>',
    )

    themes = "".join(
        f'<article class="theme"><span>0{i}</span><p>{esc(theme)}</p></article>'
        for i, theme in enumerate(digest.get("mainThemes", [])[:3], start=1)
    )
    themes_section = (
        '<section class="themes" id="themes"><div class="kicker">今日三大主线</div>'
        f'<div class="themegrid" id="themegrid">{themes}</div></section>'
    )
    text = replace_once(text, r'<section class="themes" id="themes".*?</section>', themes_section)

    cards = '<div class="grid">' + "".join(card(article, i) for i, article in enumerate(articles)) + "</div>"
    text = replace_once(text, r'<div id="news">.*?</div></main>', f'<div id="news">{cards}</div></main>')

    archive = "".join(
        f'<a class="{"active" if item.get("date") == digest.get("date") else ""}" '
        f'href="?date={esc(item.get("date"))}"><time>{esc(item.get("date"))}</time><span>查看 →</span></a>'
        for item in digests[:365]
    )
    text = replace_once(text, r'<nav id="archive">.*?</nav>', f'<nav id="archive">{archive}</nav>')
    text = replace_once(text, r'<p class="note" id="archive-note">.*?</p>', '<p class="note" id="archive-note" hidden></p>')

    watch = '<ol>' + "".join(f'<li>{esc(item)}</li>' for item in digest.get("watchNext", [])[:5]) + "</ol>"
    text = replace_once(text, r'<div id="watch">.*?</div>', f'<div id="watch">{watch}</div>')
    INDEX.write_text(text, encoding="utf-8")
    print(f"Rendered {digest.get('date')} with {len(articles)} articles")


if __name__ == "__main__":
    main()
