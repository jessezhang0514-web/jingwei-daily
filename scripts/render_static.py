#!/usr/bin/env python3
"""Build the complete text-only GitHub Pages file from the latest digest."""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
DATA = ROOT / "docs" / "data" / "digests.json"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def safe_url(value: object) -> str:
    url = str(value or "")
    return esc(url) if urlparse(url).scheme in {"http", "https"} else ""


def story_card(article: dict, position: int) -> str:
    rank = int(article.get("rank") or position + 1)
    lead = " lead" if position == 0 else ""
    url = safe_url(article.get("sourceUrl"))
    return (
        f'<article class="card{lead}"><div class="story-index"><span>{rank:02d}</span>'
        f'<small>{esc(article.get("category"))}</small></div><div class="body">'
        f'<div class="source"><span>{esc(article.get("source"))}</span>'
        f'<span>{esc(article.get("eventTime"))}</span></div>'
        f'<h3><a href="{url}" target="_blank" rel="noreferrer">{esc(article.get("title"))}</a></h3>'
        f'<p>{esc(article.get("summary"))}</p><div class="why"><strong>为什么重要</strong>'
        f'{esc(article.get("whyImportant"))}</div><div class="foot">'
        f'<a href="{url}" target="_blank" rel="noreferrer">阅读原文 ↗</a></div></div></article>'
    )


def build_page(digests: list[dict]) -> tuple[str, str, int]:
    digest = sorted(digests, key=lambda item: str(item.get("date", "")), reverse=True)[0]
    articles = sorted(digest.get("articles", []), key=lambda item: int(item.get("rank", 999)))
    if len(articles) != 20:
        raise RuntimeError(f"Expected 20 articles, found {len(articles)}")

    themes = "".join(
        f'<article class="theme"><span>0{i}</span><p>{esc(theme)}</p></article>'
        for i, theme in enumerate(digest.get("mainThemes", [])[:3], start=1)
    )
    cards = "".join(story_card(article, i) for i, article in enumerate(articles))
    archive = "".join(
        f'<a class="{"active" if item.get("date") == digest.get("date") else ""}" '
        f'href="?date={esc(item.get("date"))}"><time>{esc(item.get("date"))}</time><span>查看 →</span></a>'
        for item in sorted(digests, key=lambda item: str(item.get("date", "")), reverse=True)[:365]
    )
    watch = "".join(f"<li>{esc(item)}</li>" for item in digest.get("watchNext", [])[:5])

    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="经纬日报：按需更新的全球科技与经济重要新闻摘要">
  <title>{esc(digest.get("date"))} · 经纬日报</title>
  <style>
    :root{{--ink:#11100f;--paper:#f4f0e7;--paper2:#fbf9f4;--red:#d93c24;--green:#29483c;--line:rgba(17,16,15,.2)}}
    *{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}a{{color:inherit;text-decoration:none}}
    header{{min-height:76px;padding:15px clamp(20px,5vw,72px);display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}}.brand{{display:flex;align-items:baseline;gap:12px}}.brand b{{font:800 28px/1 "Songti SC",SimSun,serif;letter-spacing:-.08em}}.brand small,.kicker,.eyebrow{{font-size:10px;font-weight:800;letter-spacing:.16em;text-transform:uppercase}}.status{{font-size:12px;color:#5d5851}}
    .hero{{padding:clamp(48px,7vw,88px) clamp(22px,7vw,105px) 40px;position:relative;overflow:hidden}}.hero:after{{content:"20";position:absolute;z-index:-1;right:4vw;top:-3vw;font:900 clamp(150px,25vw,350px)/1 Arial;color:rgba(17,16,15,.035);letter-spacing:-.12em}}.eyebrow{{color:var(--red);margin-bottom:18px}}.hero h1{{max-width:980px;margin:0;font:700 clamp(36px,5.4vw,76px)/1.06 "Songti SC",SimSun,serif;letter-spacing:-.045em}}.hero p{{max-width:720px;margin:22px 0;line-height:1.75;color:#4b4741}}.meta{{display:flex;flex-wrap:wrap;gap:12px 28px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;font-weight:650}}
    .themes{{margin:0 clamp(22px,5vw,72px);padding:26px 0 38px;border-top:4px solid var(--ink)}}.themegrid{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:17px;background:var(--line);border:1px solid var(--line)}}.theme{{background:var(--paper);padding:25px;display:flex;gap:18px;min-height:130px}}.theme span{{color:var(--red);font:800 12px/1 monospace}}.theme p{{margin:0;font:700 19px/1.5 "Songti SC",SimSun,serif}}
    .layout{{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:clamp(30px,5vw,64px);padding:46px clamp(22px,5vw,72px) 80px;background:var(--paper2)}}.heading{{display:flex;gap:22px;align-items:end;margin-bottom:18px}}.heading h2,aside h2{{margin:5px 0 0;font:700 30px/1.1 "Songti SC",SimSun,serif}}.rule{{height:1px;background:var(--ink);flex:1;margin-bottom:7px}}
    .grid{{display:flex;flex-direction:column}}.card{{display:grid;grid-template-columns:80px minmax(0,1fr);gap:22px;border-top:1px solid var(--ink);padding:22px 0}}.story-index{{display:flex;flex-direction:column;gap:8px;align-items:flex-start}}.story-index span{{background:var(--red);color:#fff;padding:8px 9px;font:800 12px/1 monospace}}.story-index small{{font-size:10px;font-weight:800;letter-spacing:.08em}}.body{{min-width:0}}.source{{display:flex;justify-content:space-between;gap:16px;color:#746e65;font:750 10px/1.45 monospace;text-transform:uppercase}}.card h3{{margin:8px 0 10px;font:700 clamp(22px,2.2vw,30px)/1.25 "Songti SC",SimSun,serif;letter-spacing:-.02em}}.card h3 a:hover{{color:var(--red)}}.card p{{margin:0;color:#4e4942;line-height:1.68;font-size:14px}}.why{{margin-top:11px;padding:10px 0;border-top:1px solid var(--line);font-size:13px;line-height:1.55}}.why strong{{color:var(--red);margin-right:9px}}.foot{{margin-top:8px;font-size:11px;font-weight:800}}
    aside{{display:flex;flex-direction:column;gap:24px}}aside section{{padding:22px 0;border-top:4px solid var(--ink)}}aside nav{{margin-top:16px}}aside nav a{{display:flex;justify-content:space-between;padding:13px 0;border-bottom:1px solid var(--line);font:700 12px/1 monospace}}aside nav a.active{{color:var(--red)}}.watch{{background:var(--green);color:#fff;padding:24px!important;border-top-color:var(--red)!important}}.watch ol{{padding-left:20px;margin:18px 0 0}}.watch li{{padding:9px 0 12px 6px;line-height:1.55;border-bottom:1px solid rgba(255,255,255,.18)}}.sources p{{color:#615b53;font-size:13px;line-height:1.7}}.cloud{{margin-top:16px;padding-top:14px;border-top:1px solid var(--line);font:700 11px/1.9 monospace;color:#514c45}}footer{{padding:26px clamp(22px,5vw,72px);display:flex;justify-content:space-between;gap:22px;background:var(--ink);color:#eae4da;font-size:11px}}
    @media(max-width:900px){{.layout{{grid-template-columns:1fr}}aside{{display:grid;grid-template-columns:repeat(3,1fr)}}}}@media(max-width:650px){{header{{align-items:flex-start}}.brand small{{display:none}}.status{{max-width:170px;text-align:right;line-height:1.5}}.themegrid,aside{{grid-template-columns:1fr}}.card{{grid-template-columns:52px minmax(0,1fr);gap:14px}}.source{{flex-direction:column;gap:4px}}footer{{flex-direction:column}}}}
  </style>
</head>
<body>
  <header><a class="brand" href="./"><b>经纬</b><small>GLOBAL BRIEF</small></a><div class="status">按需更新 · 北京时间</div></header>
  <section class="hero"><div class="eyebrow">全球科技与经济 · 每期 20 条</div><h1 id="title">{esc(digest.get("title"))}</h1><p>从固定国际权威来源收集约 30 条候选，按影响力选出 20 条。以新闻发布时间为准，不使用无关配图。</p><div class="meta"><span id="date">{esc(digest.get("date"))}</span><span id="count">20 则新闻</span><span id="updated">更新于 {esc(digest.get("generatedAt"))}</span></div></section>
  <section class="themes" id="themes"><div class="kicker">本期三大主线</div><div class="themegrid" id="themegrid">{themes}</div></section>
  <div class="layout"><main><div class="heading"><div><div class="kicker">THE SELECTED TWENTY</div><h2>本期要闻</h2></div><span class="rule"></span></div><div id="news"><div class="grid">{cards}</div></div></main>
    <aside><section><div class="kicker">ARCHIVE</div><h2>往期日志</h2><nav id="archive">{archive}</nav></section><section class="watch"><div class="kicker">WATCH NEXT</div><h2>接下来值得关注</h2><div id="watch"><ol>{watch}</ol></div></section><section class="sources"><div class="kicker">SOURCE STANDARD</div><h2>固定来源</h2><p>每个来源原则上选 1–2 条候选，再从约 30 条候选中筛选最终 20 条。</p><div class="cloud">Reuters · AP · BBC · FT · Bloomberg · CNBC · Nikkei Asia · Nature · MIT Tech Review · The Verge · TechCrunch · IMF · World Bank · Federal Reserve · ECB</div></section></aside>
  </div><footer><span>经纬日报</span><span>固定来源 · 发布时间优先 · 按需更新</span><span>仅供信息参考，不构成投资建议</span></footer>
  <script src="./app.js" defer></script>
</body>
</html>"""
    return page, str(digest.get("date")), len(articles)


def main() -> None:
    digests = json.loads(DATA.read_text(encoding="utf-8"))
    if not digests:
        raise RuntimeError("digests.json is empty")
    page, date, count = build_page(digests)
    INDEX.write_text(page, encoding="utf-8")
    print(f"Rendered {date} with {count} articles")


if __name__ == "__main__":
    main()
