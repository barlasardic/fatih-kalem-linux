"""Settings storage and locale resolution."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from fatih_kalem import i18n
from fatih_kalem.config import DEFAULTS, Config
from tests import SRC  # noqa: F401


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = os.path.join(self._tmp.name, "settings.ini")
        # A throwaway INI keeps the developer's real preferences untouched.
        self.cfg = Config(path=self._path, auto_seed=False)

    def tearDown(self):
        self._tmp.cleanup()

    def test_defaults_are_typed(self):
        self.assertEqual(self.cfg.get("pen/color"), DEFAULTS["pen/color"])
        self.assertIsInstance(self.cfg.get_float("pen/width"), float)
        self.assertIsInstance(self.cfg.get_bool("overlay/keepAbove"), bool)

    def test_set_round_trips(self):
        self.cfg.set("pen/color", "#123456")
        self.cfg.set("pen/width", 12.5)
        self.assertEqual(self.cfg.get("pen/color"), "#123456")
        self.assertAlmostEqual(self.cfg.get_float("pen/width"), 12.5)

    def test_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            self.cfg.get("pen/nope")
        with self.assertRaises(KeyError):
            self.cfg.set("pen/nope", 1)

    def test_corrupt_value_falls_back_to_the_default(self):
        self.cfg._s.setValue("pen/width", "not-a-number")
        self.assertAlmostEqual(self.cfg.get_float("pen/width"), DEFAULTS["pen/width"])

    def test_bool_strings_from_ini_are_coerced(self):
        self.cfg._s.setValue("overlay/keepAbove", "false")
        self.assertFalse(self.cfg.get_bool("overlay/keepAbove"))
        self.cfg._s.setValue("overlay/keepAbove", "true")
        self.assertTrue(self.cfg.get_bool("overlay/keepAbove"))

    def test_seed_missing_writes_every_default(self):
        self.cfg._s.clear()
        written = self.cfg.seed_missing()
        self.assertEqual(written, len(DEFAULTS))
        self.assertEqual(self.cfg.seed_missing(), 0)

    def test_is_default(self):
        self.assertTrue(self.cfg.is_default("pen/penType"))
        self.cfg.set("pen/penType", "dashed")
        self.assertFalse(self.cfg.is_default("pen/penType"))

    def test_list_access(self):
        self.cfg.set("pen/favoriteColors", "#111111,#222222,#333333")
        self.assertEqual(self.cfg.get_list("pen/favoriteColors")[1], "#222222")

    def test_reset_restores_defaults(self):
        self.cfg.set("pen/color", "#abcdef")
        self.cfg.reset()
        self.assertEqual(self.cfg.get("pen/color"), DEFAULTS["pen/color"])

    def test_every_default_is_typed_consistently(self):
        for key, default in DEFAULTS.items():
            self.assertIn("/", key, "settings keys are namespaced")
            self.assertIsInstance(self.cfg.get(key), type(default), key)

    def test_overlay_hint_and_board_color_exist(self):
        """Keys used by the overlay must be declared, or get() would raise."""
        for key in ("overlay/hint", "overlay/boardColor", "general/singleInstance"):
            self.assertIn(key, DEFAULTS)


class LocaleTests(unittest.TestCase):
    def test_normalise_common_spellings(self):
        self.assertEqual(i18n.normalise_locale("tr_TR.UTF-8"), "tr_TR")
        self.assertEqual(i18n.normalise_locale("tr-TR"), "tr_TR")
        self.assertEqual(i18n.normalise_locale("en_GB"), "en_US", "falls back to the language")
        self.assertEqual(i18n.normalise_locale("C"), "")

    def test_detect_from_environment(self):
        with mock.patch.dict(os.environ, {"LANG": "tr_TR.UTF-8"}, clear=False):
            self.assertEqual(i18n.detect_system_locale(), "tr_TR")

    def test_resolve_explicit_preference(self):
        self.assertEqual(i18n.resolve_locale("en_US"), "en_US")

    def test_resolve_system_falls_back_to_turkish(self):
        with mock.patch.dict(
            os.environ, {"LANG": "C", "LC_ALL": "", "LC_MESSAGES": ""}, clear=False
        ):
            self.assertEqual(i18n.resolve_locale("system"), "tr_TR")

    def test_catalogs_have_the_same_keys_as_english_source(self):
        turkish = set(i18n.CATALOGS["tr_TR"])
        english = set(i18n.CATALOGS["en_US"])
        self.assertEqual(english, set(), "en_US is the source language and needs no entries")
        for source in ("Pen", "Eraser", "Undo", "Redo"):
            self.assertIn(source, turkish)


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        i18n.install(i18n.DEFAULT_LOCALE)

    def test_turkish_lookup(self):
        i18n.install("tr_TR")
        self.assertEqual(i18n.tr("Undo"), "Geri al")
        self.assertEqual(i18n.tr("eraser"), "Silgi")

    def test_english_passes_through(self):
        i18n.install("en_US")
        self.assertEqual(i18n.tr("Undo"), "Undo")

    def test_unknown_string_is_returned_verbatim(self):
        i18n.install("tr_TR")
        self.assertEqual(i18n.tr("A brand new string"), "A brand new string")

    def test_unknown_locale_falls_back(self):
        self.assertEqual(i18n.install("de_DE").locale_name, i18n.DEFAULT_LOCALE)

    def test_ts_skeleton_is_written(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "tr_TR.ts"
            count = i18n.write_ts_skeleton(target, "tr_TR")
            self.assertGreater(count, 5)
            text = target.read_text(encoding="utf-8")
            self.assertIn('<TS version="2.1" language="tr-TR">', text)
            self.assertIn("<source>Undo</source>", text)
            self.assertIn("<translation>Geri al</translation>", text)


if __name__ == "__main__":
    unittest.main()
