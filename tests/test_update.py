import copy
from datetime import datetime
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from update import validate, canonical, check_page
from render_static import build_page

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.d = {'date': '2026-09-06', 'title': '测试简报', 'mainThemes': ['一', '二', '三'],
            'watchNext': ['下一步'], 'windowStart': '2026-09-05T08:00:00+08:00',
            'windowEnd': '2026-09-06T08:00:00+08:00', 'articles': []}
        for n in range(1, 21):
            self.d['articles'].append({'id': f'2026-09-06-{n:02d}', 'rank': n,
                'region': '中国' if n <= 5 else '国际', 'category': '科技', 'title': f'新闻{n}',
                'summary': '事实摘要', 'whyImportant': '影响', 'eventTime': '2026-09-05',
                'source': 'AP', 'sourceUrl': f'https://apnews.com/article/example-{n}',
                'publishedAt': '2026-09-05T12:00:00+08:00',
                'evidence': {'title': 'Original headline', 'note': '事实笔记', 'checkedAt': '2026-09-06T08:00:00+08:00'}})
        self.now = datetime.fromisoformat('2026-09-06T09:00:00+08:00')

    def test_valid(self):
        validate(self.d, now=self.now)
        page, _, count = build_page([self.d])
        check_page(page, self.d)
        self.assertEqual(count, 20)
        self.assertIn('archive/2026-09-06.html', page)

    def test_invalid_inputs_blocked(self):
        for change in [lambda d: d['articles'].pop(),
                       lambda d: d['articles'][0].update(region='国际'),
                       lambda d: d['articles'][0].update(sourceUrl='https://apnews.com/'),
                       lambda d: d['articles'][0].update(sourceUrl=d['articles'][1]['sourceUrl'] + '?utm_source=x'),
                       lambda d: d['articles'][0].update(publishedAt='2026-09-04T12:00:00+08:00'),
                       lambda d: d['articles'][0].update(evidence={}),
                       lambda d: d['articles'][0].update(rank=2)]:
            d = copy.deepcopy(self.d)
            change(d)
            with self.assertRaises(ValueError):
                validate(d, now=self.now)

    def test_page_mismatch(self):
        page, _, _ = build_page([self.d])
        with self.assertRaises(ValueError):
            check_page(page.replace('新闻1', '错误标题'), self.d)

    def test_canonical(self):
        self.assertEqual(canonical('https://www.apnews.com/article/a/?utm_source=x#top'),
                         canonical('https://apnews.com/article/a'))

if __name__ == '__main__':
    unittest.main()
