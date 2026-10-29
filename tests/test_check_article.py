import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_article  # noqa: E402

TODAY = dt.date(2026, 10, 29)
GOOD = ROOT / "tests" / "fixtures" / "good-comparison.md"


def check_text(tmp: Path, text: str) -> check_article.Result:
    path = tmp / "article.md"
    path.write_text(text, encoding="utf-8")
    return check_article.check(path, TODAY)


class CheckArticleTest(unittest.TestCase):
    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.good = GOOD.read_text(encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_good_article_passes(self):
        res = check_article.check(GOOD, TODAY)
        self.assertEqual(res.errors, [])
        self.assertEqual(res.warnings, [])

    def test_templates_fail_until_filled(self):
        for name in ("note-comparison.md", "note-ranking.md"):
            res = check_article.check(ROOT / "templates" / name, TODAY)
            self.assertTrue(res.errors, name)

    def test_missing_pr_notice(self):
        res = check_text(self.tmp, self.good.replace("※本記事はアフィリエイト広告（PR）を含みます\n", ""))
        self.assertTrue(any("PR表記" in e for e in res.errors))

    def test_banned_word(self):
        res = check_text(self.tmp, self.good.replace("電気代。", "これは神家電です。"))
        self.assertTrue(any("神家電" in e for e in res.errors))

    def test_price_without_writing_date(self):
        res = check_text(self.tmp, self.good.replace("価格は記事執筆時点の目安です。", ""))
        self.assertTrue(any("記事執筆時点" in e for e in res.errors))

    def test_unchecked_recall(self):
        res = check_text(self.tmp, self.good.replace("recall_checked: 2026-10-28", "recall_checked: YYYY-MM-DD"))
        self.assertTrue(any("recall_checked" in e for e in res.errors))

    def test_stale_price_check_warns(self):
        res = check_text(self.tmp, self.good.replace("prices_checked: 2026-10-28", "prices_checked: 2026-09-01"))
        self.assertEqual(res.errors, [])
        self.assertTrue(any("prices_checked" in w for w in res.warnings))

    def test_weak_link_text_warns(self):
        res = check_text(self.tmp, self.good.replace("[サンプルA]", "[詳しくはこちら]"))
        self.assertTrue(any("詳しくはこちら" in w for w in res.warnings))

    def test_needs_check_marker(self):
        res = check_text(self.tmp, self.good.replace("30cm", "【要確認】"))
        self.assertTrue(any("要確認" in e for e in res.errors))


if __name__ == "__main__":
    unittest.main()
