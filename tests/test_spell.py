import unittest

from hebbot import content as content_lib
from hebbot import spell


@unittest.skipUnless(spell.available(), "hspell is not installed")
class SpellTests(unittest.TestCase):
    def test_the_library_has_no_unexplained_misspellings(self):
        problems = spell.check(content_lib.load_content())
        self.assertEqual(problems, [], "fix the spelling, or add a checked word to content/spell-allow.txt")

    def test_it_really_catches_the_kind_of_error_we_had(self):
        bad = spell.misspelled(["צואר", "קרסל", "כסא", "שולחן", "אוזן"])
        self.assertIn("צואר", bad)          # צוואר
        self.assertIn("קרסל", bad)          # קרסול
        self.assertIn("כסא", bad)           # כיסא
        self.assertNotIn("שולחן", bad)
        self.assertNotIn("אוזן", bad)
        self.assertIn("צוואר", bad["צואר"])


class SpellHelperTests(unittest.TestCase):
    def test_tokens_split_sentences_strip_nikud_and_ignore_punctuation(self):
        content = {"themes": {"t": {"words": [{"id": "w", "he": "שֻׁלְחָן"}],
                                    "sentences": [{"he": "אני אוהב, באמת!"}]}}, "roots": []}
        self.assertEqual(set(spell.tokens(content)), {"אני", "אוהב", "באמת", "שלחן"})

    def test_allow_list_ignores_comments_and_blank_lines(self):
        self.assertIn("באסה", spell.load_allow())
        self.assertNotIn("", spell.load_allow())


if __name__ == "__main__":
    unittest.main()
