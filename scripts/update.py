#!/usr/bin/env python3
"""Prepare, publish and verify a digest using Python's standard library."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen

from render_static import ROOT, build_page

BJ = timezone(timedelta(hours=8))
DAILY = ROOT / 'docs/data/daily'
CACHE = ROOT / '.cache'
SOURCE_DOMAINS = {'reuters.com', 'apnews.com', 'bbc.com', 'bbc.co.uk', 'ft.com',
    'bloomberg.com', 'bloomberglaw.com', 'wsj.com', 'economist.com', 'nikkei.com',
    'cnbc.com', 'imf.org', 'worldbank.org', 'oecd.org', 'bis.org', 'federalreserve.gov',
    'ecb.europa.eu', 'technologyreview.com', 'nature.com', 'science.org', 'ieee.org',
    'wired.com', 'arstechnica.com', 'theverge.com', 'techcrunch.com', 'bls.gov',
    'ec.europa.eu', 'destatis.de', 'statcan.gc.ca', 'restofworld.org',
    'bleepingcomputer.com', 'nasa.gov', 'esa.int', 'sec.gov', 'nhtsa.gov',
    'nbim.no', 'blog.google', 'openai.com', 'anthropic.com', 'nvidia.com',
    'microsoft.com', 'apple.com', 'fda.gov'}
SECTION_PATHS = {'', '/', '/news', '/technology', '/business', '/world', '/markets', '/river'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    value = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if not path.exists() or path.read_text(encoding='utf-8') != value:
        path.write_text(value, encoding='utf-8')

def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('时间必须带时区')
    return result

def canonical(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.startswith('utm_') and k not in {'fbclid', 'gclid'}]
    return urlunsplit(('https', p.netloc.lower().removeprefix('www.'), p.path.rstrip('/'), urlencode(sorted(query)), ''))

def direct_url(url):
    p = urlsplit(url)
    host = (p.hostname or '').lower()
    if p.scheme not in {'http', 'https'} or p.username or not any(host == d or host.endswith('.' + d) for d in SOURCE_DOMAINS):
        raise ValueError(f'非允许的权威来源: {url}')
    if p.path.rstrip('/') in SECTION_PATHS or '/search' in p.path:
        raise ValueError(f'需要文章直达链接: {url}')
    return canonical(url)

def validate(digest, previous=None, now=None):
    now = now or datetime.now(BJ)
    day = datetime.strptime(digest['date'], '%Y-%m-%d').date()
    if day > now.date():
        raise ValueError('简报日期不能在未来')
    start, end = timestamp(digest['windowStart']), timestamp(digest['windowEnd'])
    if not start < end <= now or end.astimezone(BJ).date() != day:
        raise ValueError('时间窗口无效或超过当前时间')
    if previous:
        boundary = previous.get('windowStart') if previous['date'] == digest['date'] else previous.get('windowEnd')
        if boundary and start != timestamp(boundary):
            raise ValueError('时间窗口必须衔接上期截止点；同日重做沿用起点')
    for key in ('title', 'mainThemes', 'watchNext'):
        if not digest.get(key):
            raise ValueError(f'缺少 {key}')
    articles = digest['articles']
    if len(articles) != 20 or sorted(a['rank'] for a in articles) != list(range(1, 21)):
        raise ValueError('必须20条且排名覆盖1–20')
    if Counter(a.get('region') for a in articles) != {'中国': 5, '国际': 15}:
        raise ValueError('必须5条中国、15条国际')
    seen, titles = set(), set()
    for a in articles:
        for key in ('id', 'category', 'title', 'summary', 'whyImportant', 'eventTime', 'source'):
            if not isinstance(a.get(key), str) or not a[key].strip():
                raise ValueError(f'第{a["rank"]}条缺少 {key}')
        if a['id'] != f'{digest["date"]}-{a["rank"]:02d}':
            raise ValueError('id与日期排名不一致')
        if not start < timestamp(a['publishedAt']) <= end:
            raise ValueError(f'发布时间超出本期窗口: {a["title"]}')
        evidence = a.get('evidence', {})
        if not evidence.get('title') or not evidence.get('note'):
            raise ValueError('缺少原文标题或核验笔记')
        checked = timestamp(evidence.get('checkedAt', ''))
        if not timestamp(a['publishedAt']) <= checked <= now:
            raise ValueError('核验时间无效')
        url = direct_url(a['sourceUrl'])
        title = ''.join(a['title'].split())
        if url in seen or title in titles:
            raise ValueError('同一原文或标题重复')
        seen.add(url)
        titles.add(title)
        if a.get('secondaryUrl'):
            direct_url(a['secondaryUrl'])
        if a.get('imageUrl'):
            raise ValueError('当前使用纯文字模式')

def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'JingweiDaily/1.0'}), timeout=20) as response:
        return response.geturl(), response.read(2_000_000).decode('utf-8', errors='replace')

def check_links(digest):
    path = CACHE / 'links.json'
    cache = read(path) if path.exists() else {}
    now = datetime.now(BJ)
    urls = {a[k] for a in digest['articles'] for k in ('sourceUrl', 'secondaryUrl') if a.get(k)}
    pending = [u for u in urls if not cache.get(u) or now - timestamp(cache[u]) > timedelta(hours=24)]
    def check(url):
        try:
            final, body = fetch(url)
            direct_url(final)
            if not body.strip():
                raise ValueError('空页面')
            return url, None
        except Exception as exc:
            return url, str(exc)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, pending))
    failures = []
    for url, error in results:
        if error:
            failures.append(f'{url}: {error}')
        else:
            cache[url] = now.isoformat()
    write(path, cache)
    if failures:
        raise ValueError('链接检查未通过（未写入发布文件）:\n' + '\n'.join(failures))

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = 0
        self.headings = []
        self.in_heading = False
        self.text = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'card' in attrs.get('class', '').split():
            self.cards += 1
        if tag == 'h3':
            self.in_heading = True
            self.headings.append('')
    def handle_endtag(self, tag):
        if tag == 'h3':
            self.in_heading = False
    def handle_data(self, text):
        self.text.append(text)
        if self.in_heading:
            self.headings[-1] += text

def check_page(html, digest):
    page = Page()
    page.feed(html)
    expected = [a['title'] for a in sorted(digest['articles'], key=lambda a: a['rank'])]
    if page.cards != len(expected) or page.headings != expected or digest['date'] not in page.text:
        raise ValueError('页面日期、正文数量或标题与数据不一致')

def history():
    return [read(p) for p in sorted(DAILY.glob('*.json'), reverse=True)][:365]

def render(digests, current, all_pages=False):
    page, date, count = build_page(digests)
    check_page(page, digests[0])
    write(ROOT / 'docs/index.html', page)
    for d in digests if all_pages else [current]:
        page, _, _ = build_page(digests, d, '../')
        check_page(page, d)
        write(ROOT / f'docs/archive/{d["date"]}.html', page)
    write(ROOT / 'docs/data/index.json', [{'date': d['date'], 'title': d['title']} for d in digests])
    print(f'Rendered {date} with {count} articles')

def manifest():
    paths = [ROOT / 'docs/index.html', ROOT / 'docs/data/index.json']
    paths += list(DAILY.glob('*.json')) + list((ROOT / 'docs/archive').glob('*.html'))
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in paths}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).rstrip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['status', 'migrate', 'prepare', 'publish', 'verify'])
    parser.add_argument('draft', nargs='?')
    parser.add_argument('--url', default='https://jessezhang0514-web.github.io/jingwei-daily/')
    args = parser.parse_args()
    digests = history()
    if args.command == 'status':
        status = {k: digests[0].get(k) for k in ('date', 'windowStart', 'windowEnd', 'generatedAt')} if digests else {'migrationRequired': True}
        if digests and not status.get('windowEnd'):
            status['suggestedWindowStart'] = digests[0]['date'] + 'T00:00:00+08:00'
            status['note'] = '旧期无可靠检索截止时间；首次使用日期零点，轻量排除上期已收录URL，之后严格衔接windowEnd。'
        print(json.dumps(status, ensure_ascii=False))
    elif args.command == 'migrate':
        if digests:
            raise ValueError('已迁移，拒绝重复覆盖')
        legacy = read(ROOT / 'docs/data/digests.json')
        for d in legacy:
            datetime.strptime(d['date'], '%Y-%m-%d')
            write(DAILY / f'{d["date"]}.json', d)
        digests = history()
        render(digests, digests[0], all_pages=True)
        write(CACHE / 'prepared.json', {'migration': True, 'files': manifest()})
    elif args.command == 'prepare':
        if not digests or not args.draft:
            raise ValueError('先迁移，并提供草稿路径')
        d = read(Path(args.draft))
        if d['date'] < digests[0]['date']:
            raise ValueError('不补历史日期')
        validate(d, digests[0])
        check_links(d)
        d['generatedAt'] = datetime.now(BJ).strftime('%Y-%m-%d %H:%M 北京时间')
        write(DAILY / f'{d["date"]}.json', d)
        render(history(), d)
        write(CACHE / 'prepared.json', {'migration': False, 'files': manifest()})
    elif args.command == 'publish':
        prepared = read(CACHE / 'prepared.json')
        if prepared['files'] != manifest():
            raise ValueError('准备后的文件已变化，请重新prepare')
        if not prepared['migration']:
            validate(digests[0])
        for p in ('docs/index.html', f'docs/archive/{digests[0]["date"]}.html'):
            check_page((ROOT / p).read_text(), digests[0])
        if git('branch', '--show-current') != 'main':
            raise ValueError('发布分支必须为main')
        allowed = ('docs/', 'scripts/', 'tests/', 'UPDATE_POLICY.md', 'AGENTS.md', '.gitignore')
        changes = git('status', '--porcelain')
        if any(not line[3:].startswith(allowed) for line in changes.splitlines()):
            raise ValueError('存在流程之外的修改，停止自动提交')
        git('add', '--', 'docs', 'scripts', 'UPDATE_POLICY.md', 'AGENTS.md', '.gitignore')
        if (ROOT / 'tests').exists():
            git('add', '--', 'tests')
        if git('diff', '--cached', '--name-only'):
            git('commit', '-m', f'Update digest workflow: {digests[0]["date"]}')
        print(git('push', 'origin', 'main'))
        print('提交已推送；仍须运行verify确认上线')
    elif args.command == 'verify':
        for suffix in ('', f'archive/{digests[0]["date"]}.html'):
            _, page = fetch(args.url.rstrip('/') + '/' + suffix + '?verify=' + datetime.now(BJ).strftime('%H%M%S'))
            check_page(page, digests[0])
        print(f'Verified {digests[0]["date"]}: 20 article cards, home and archive')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit(str(exc))
