import ast
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PIL import ImageFont


SOURCE = Path(__file__).resolve().parents[1] / "yolomedia.py"
LINUX_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


class ChineseOverlayTests(unittest.TestCase):
    def setUp(self):
        # Load the actual overlay functions without starting audio or importing model runtimes.
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        functions = {"_init_font", "_ui_next_y_top", "draw_text_cn"}
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in functions]
        self.overlay = {
            "os": os, "cv2": cv2, "np": np,
            "_PIL_OK": False, "_FONT_PATH": None,
            "UNIFIED_FONT_PX": 12, "_UI_TOP_MARGIN": 12,
            "_UI_RIGHT_MARGIN": 12, "_UI_TR_LINE": 0,
        }
        exec(compile(tree, str(SOURCE), "exec"), self.overlay)

    def test_macos_pingfang_is_selected(self):
        font = "/System/Library/Fonts/PingFang.ttc"
        with patch("os.path.exists", side_effect=lambda path: path == font):
            self.overlay["_init_font"]()
        self.assertTrue(self.overlay["_PIL_OK"])
        self.assertEqual(self.overlay["_FONT_PATH"], font)

    def test_windows_font_keeps_priority(self):
        font = r"C:\\Windows\\Fonts\\msyh.ttc"
        with patch("os.path.exists", return_value=True):
            self.overlay["_init_font"]()
        self.assertEqual(self.overlay["_FONT_PATH"], font)

    def test_missing_fonts_preserve_opencv_fallback(self):
        with patch("os.path.exists", return_value=False):
            self.overlay["_init_font"]()
        self.assertFalse(self.overlay["_PIL_OK"])
        self.assertIsNone(self.overlay["_FONT_PATH"])

    @unittest.skipUnless(os.path.isfile(LINUX_FONT), "Noto Sans CJK font is not installed")
    def test_installed_cjk_font_renders_distinct_chinese_glyphs(self):
        self.overlay["_init_font"]()
        images = []
        for text in ("中", "文"):
            self.overlay["_UI_TR_LINE"] = 0
            image = np.zeros((80, 160, 3), dtype=np.uint8)
            self.overlay["draw_text_cn"](image, text, (0, 0))
            self.assertTrue(image.any())
            images.append(image)
        self.assertFalse(np.array_equal(images[0], images[1]))


if __name__ == "__main__":
    unittest.main()
