import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voc.analyze import (code_all, coding_quality, dedupe, extract_price, load_codebook, price_ceiling,
                         price_curve, stance_of, summarize)
from voc.scripts import lint, lint_playbook, load_scripts
from voc.synth import Comment, generate


class AnalyzeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = load_codebook()
        cls.raw = generate(600, seed=4)
        cls.kept, cls.dups = dedupe(cls.raw)
        cls.coded = code_all(cls.kept, cls.cb)

    def test_dedupe_merges_likes(self):
        a = Comment(1, "溜背好看", 10, "广东", {"design"}, "pos")
        b = Comment(2, "溜背好看！", 5, "浙江", {"design"}, "pos")
        kept, n = dedupe([a, b])
        self.assertEqual((len(kept), n, kept[0].likes), (1, 1, 15))
        self.assertEqual(a.likes, 10)

    def test_noise_is_dropped(self):
        texts = {c.text for c in self.coded}
        self.assertNotIn("沙发", texts)
        self.assertGreater(self.dups, 0)

    def test_stance_with_negation(self):
        self.assertEqual(stance_of("9 系不会差的", self.cb), "pos")
        self.assertEqual(stance_of("超过 40 万就别费事生产了", self.cb), "neg")
        self.assertEqual(stance_of("外观要看实车", self.cb), "neu")

    def test_price_extraction(self):
        self.assertEqual(extract_price("42.98 万起？劝退"), 42.98)
        self.assertIsNone(extract_price("第 3 万条评论"))

    def test_price_ceiling_near_40(self):
        ceiling = price_ceiling(price_curve(self.coded), min_n=5)
        self.assertIsNotNone(ceiling)
        self.assertTrue(38 <= ceiling <= 43, ceiling)

    def test_coding_quality(self):
        for key, q in coding_quality(self.coded, self.kept, self.cb).items():
            self.assertGreaterEqual(q["recall"], 0.8, key)
            self.assertGreaterEqual(q["precision"], 0.6, key)

    def test_like_weighting_bounds(self):
        for s in summarize(self.coded, self.cb):
            self.assertTrue(0 <= s.like_neg_rate <= 1)
            self.assertEqual(s.quotes, sorted(s.quotes, key=lambda c: -c.likes))


class ScriptsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_scripts()

    def test_playbook_is_clean(self):
        self.assertEqual(lint_playbook(self.cfg), [])

    def test_lint_catches_drafts(self):
        flagged = [d for d in self.cfg["drafts"] if lint(d["text"], self.cfg)]
        self.assertEqual(len(flagged), 3)
        self.assertEqual(len(lint("以后肯定涨价，网上都是黑子", self.cfg)), 2)


if __name__ == "__main__":
    unittest.main()
