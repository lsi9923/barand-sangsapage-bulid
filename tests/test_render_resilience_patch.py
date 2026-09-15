from __future__ import annotations

import html
import re
import types
import unittest
import urllib.parse
from pathlib import Path

from tools import patch_render_resilience_exe as patcher


RUNTIME_GLOBALS = {
    "Path": Path,
    "html": html,
    "re": re,
    "urllib": types.SimpleNamespace(parse=urllib.parse),
}


def runtime_function(name: str):
    source = getattr(patcher, name)
    return types.FunctionType(patcher.compiled_function(source), dict(RUNTIME_GLOBALS))


class HeaderDummy:
    def _is_url(self, value):
        return str(value or "").startswith(("http://", "https://"))

    def _normalize_excel_header(self, value):
        return re.sub(r"[\s_\-()/]+", "", str(value or "").strip()).lower()

    @staticmethod
    def _is_ownerclan_ui_image_src(value):
        return False

    @staticmethod
    def _looks_like_recommendation_image(value):
        return False


class Page:
    def __init__(self, url, closed=False):
        self.url = url
        self.closed = closed

    def is_closed(self):
        return self.closed


class Context:
    def __init__(self, pages):
        self.pages = pages


class RenderResiliencePatchTests(unittest.TestCase):
    def test_header_recognizes_generic_supplier_columns_without_stealing_image_columns(self):
        function = runtime_function("_patched_is_1688_url_header")
        self.assertTrue(function(HeaderDummy(), "공급처 URL"))
        self.assertTrue(function(HeaderDummy(), "Supplier Product Source"))
        self.assertFalse(function(HeaderDummy(), "상품 이미지 URL"))

    def test_existing_page_skips_closed_wrappers(self):
        function = runtime_function("_patched_existing_page_for_url")
        closed = Page("https://shop.example.com/item/1", closed=True)
        valid = Page("https://shop.example.com/item/2")
        result = function(types.SimpleNamespace(), Context([closed, valid]), "https://shop.example.com/item/3")
        self.assertIs(result, valid)

    def test_generic_source_images_are_ranked_and_ui_assets_are_rejected(self):
        function = runtime_function("_patched_rank_1688_image_candidates")
        candidate = {
            "src": "https://cdn.vendor.example/assets/product-main.webp",
            "alt": "상품",
            "width": 900,
            "height": 900,
            "client_width": 600,
            "client_height": 600,
            "top": 10,
            "parent_chain": "IMG",
        }
        icon = dict(candidate, src="https://cdn.vendor.example/assets/icon.webp", width=32, height=32)
        result = function(types.SimpleNamespace(), [icon, candidate], ["https://media.vendor.example/images/detail-02.jpg"])
        sources = [str(item["src"]) for item in result]
        self.assertIn(candidate["src"], sources)
        self.assertIn("https://media.vendor.example/images/detail-02.jpg", sources)
        self.assertNotIn(icon["src"], sources)

    def test_generic_primary_and_detail_candidates_do_not_require_known_hosts(self):
        primary = runtime_function("_patched_primary_product_image_candidate")
        detail = runtime_function("_patched_product_detail_image_candidate")
        record = {
            "src": "https://shop.vendor.example/assets/product-01.webp",
            "alt": "상품",
            "width": 1200,
            "height": 1200,
            "client_width": 700,
            "client_height": 700,
            "top": 120,
            "parent_chain": "DIV.product-main > IMG",
        }
        dummy = HeaderDummy()
        self.assertTrue(primary(dummy, record))
        self.assertTrue(detail(dummy, record))

    def test_generic_detail_html_urls_are_extracted_without_domain_allowlist(self):
        function = runtime_function("_patched_extract_detail_image_urls")
        html_text = (
            '<img src="https://media.vendor.example/item/detail-01.webp">'
            '<img src="https://media.vendor.example/item/icon.webp">'
        )
        result = function(HeaderDummy(), html_text, "https://shop.vendor.example/item/1")
        self.assertEqual(result, ["https://media.vendor.example/item/detail-01.webp"])

    def test_generic_source_payload_is_usable_after_local_download(self):
        function = runtime_function("_patched_source_payload_usable")
        with self.subTest("local source image"):
            path = Path("vendor-product-image.png")
            dummy = types.SimpleNamespace(_is_valid_image_file=lambda value: value == path)
            payload = {
                "title": "Vendor product",
                "text": "",
                "image_urls": [],
                "source_image_paths": [str(path)],
                "downloaded_images": [],
            }
            self.assertTrue(function(dummy, payload))

    def test_submit_patch_contains_single_lifecycle_retry_and_context_rebind(self):
        code = patcher.lifecycle_retry_submit_code()
        strings = set()

        def collect(value):
            for item in value.co_consts:
                if isinstance(item, str):
                    strings.add(item)
                elif isinstance(item, tuple):
                    strings.update(part for part in item if isinstance(part, str))
                elif isinstance(item, type(value)):
                    collect(item)

        collect(code)
        self.assertIn("event loop is closed", strings)
        self.assertIn("_active_playwright_context", strings)
        self.assertIn("allow_retry", code.co_varnames)


if __name__ == "__main__":
    unittest.main(verbosity=2)
