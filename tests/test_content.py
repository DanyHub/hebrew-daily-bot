import copy
import unittest

from hebbot import content as content_lib
from hebbot import render


class ContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()

    def test_library_is_valid(self):
        self.assertEqual(content_lib.validate(self.content), [])

    def test_both_levels_have_packs_and_a_root(self):
        for level in content_lib.LEVELS:
            self.assertGreaterEqual(len(content_lib.build_packs(self.content, level)), 2)
            self.assertGreaterEqual(len(content_lib.roots_for_level(self.content, level)), 1)

    def test_packs_respect_max_size(self):
        for level in content_lib.LEVELS:
            for pack in content_lib.build_packs(self.content, level):
                self.assertLessEqual(len(pack["words"]), content_lib.MAX_PACK_SIZE)

    def test_family_lookup(self):
        family = content_lib.family_of(self.content, "ktv")
        self.assertGreaterEqual(len(family), 4)
        self.assertEqual(content_lib.family_of(self.content, "nope"), [])

    def test_strip_nikud(self):
        self.assertEqual(content_lib.strip_nikud("שָׁלַח"), "שלח")


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.content = copy.deepcopy(content_lib.load_content())

    def test_detects_missing_translation(self):
        self.content["themes"]["body"]["words"][0]["meaning"].pop("en")
        self.assertTrue(any("meaning.en" in e for e in content_lib.validate(self.content)))

    def test_nikud_is_optional(self):
        self.content["themes"]["body"]["words"][0]["he"] = "ראש"
        self.assertEqual(content_lib.validate(self.content), [])

    def test_detects_non_hebrew_text(self):
        self.content["themes"]["body"]["words"][0]["he"] = "head"
        self.assertTrue(any("no Hebrew letters" in e for e in content_lib.validate(self.content)))

    def test_detects_duplicate_id(self):
        words = self.content["themes"]["body"]["words"]
        words[1]["id"] = words[0]["id"]
        self.assertTrue(any("duplicate id" in e for e in content_lib.validate(self.content)))

    def test_detects_unknown_root_reference(self):
        self.content["themes"]["body"]["words"][0]["root"] = "zzz"
        self.assertTrue(any("unknown root" in e for e in content_lib.validate(self.content)))

    def test_detects_bad_level(self):
        self.content["themes"]["body"]["words"][0]["level"] = 9
        self.assertTrue(any("level must be" in e for e in content_lib.validate(self.content)))


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()

    def test_every_pack_and_root_renders_in_both_languages(self):
        for lang in content_lib.LANGS:
            for level in content_lib.LEVELS:
                for pack in content_lib.build_packs(self.content, level):
                    text = render.render_pack(pack, lang)
                    self.assertLessEqual(len(text), content_lib.TELEGRAM_MAX_LEN)
                    self.assertIn(pack["words"][0]["he"], text)
                for root in content_lib.roots_for_level(self.content, level):
                    text = render.render_root(root, lang)
                    self.assertLessEqual(len(text), content_lib.TELEGRAM_MAX_LEN)

    def test_language_is_respected(self):
        pack = next(p for p in content_lib.build_packs(self.content, 1) if p["theme"] == "body")
        self.assertIn("Tête", render.render_pack(pack, "fr"))
        self.assertNotIn("Tête", render.render_pack(pack, "en"))
        self.assertIn("Head", render.render_pack(pack, "en"))

    def test_html_special_characters_are_escaped(self):
        pack = copy.deepcopy(content_lib.build_packs(self.content, 1)[0])
        pack["words"][0]["meaning"]["en"] = "A <b>&</b> _bold_ *star*"
        text = render.render_pack(pack, "en")
        self.assertIn("A &lt;b&gt;&amp;&lt;/b&gt; _bold_ *star*", text)

    def test_unknown_language_rejected(self):
        pack = content_lib.build_packs(self.content, 1)[0]
        with self.assertRaises(ValueError):
            render.render_pack(pack, "de")

    def test_root_without_examples_renders_family_and_source(self):
        root = next(r for r in self.content["roots"] if r["id"] == "rkv")
        self.assertTrue(all("example" not in w for w in root["words"]))
        text = render.render_root(root, "en")
        self.assertIn("Source:", text)
        self.assertIn("hebreu.org", text)
        self.assertNotIn("🇮🇱", text)
        self.assertEqual(text.count("<b>") - 3, len(root["words"]))  # title, root meaning, family heading + one per word

    def test_root_with_examples_still_shows_them(self):
        root = next(r for r in self.content["roots"] if r["id"] == "ktv")
        self.assertIn("🇮🇱", render.render_root(root, "fr"))

    def test_packs_show_their_sentences(self):
        for level in content_lib.LEVELS:
            for pack in content_lib.build_packs(self.content, level):
                self.assertGreaterEqual(len(pack["sentences"]), 3, pack["theme"])
                text = render.render_pack(pack, "fr")
                self.assertIn("En phrases", text)
                for sentence in pack["sentences"]:
                    self.assertIn(sentence["he"], text)
                    self.assertEqual(sentence["level"], level)

    def test_sentences_mostly_reuse_the_packs_words(self):
        """Every sentence should contain at least one word of its pack (prefixes like ה/ב/ל allowed)."""
        for level in content_lib.LEVELS:
            for pack in content_lib.build_packs(self.content, level):
                for sentence in pack["sentences"]:
                    hits = sum(1 for w in pack["words"] if w["he"] in sentence["he"])
                    self.assertGreaterEqual(hits, 1, f"{pack['theme']} L{level}: {sentence['he']}")

    def test_root_letters_formatting(self):
        self.assertEqual(render.format_root_letters("כתב"), "כ־ת־ב")


if __name__ == "__main__":
    unittest.main()
