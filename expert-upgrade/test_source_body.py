import json
import marshal
import unittest

from playwright.sync_api import sync_playwright, Error
import build_upgrade as b


def main_code(path):
    entry = next(e for e in b.read_archive(path).entries if e.name == 'detail_page_automation_gui')
    return marshal.loads(b.entry_payload(entry))


class SourceBodyTests(unittest.TestCase):
    def test_scrapers_read_main_body_when_extension_adds_shadow_body(self):
        code = main_code(b.TARGET)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome',headless=True)
            try:
                page = browser.new_page()
                page.set_content('<html><body><main>PRODUCT_BODY</main><hypeduck-coupang-badge></hypeduck-coupang-badge></body></html>')
                page.evaluate("""() => {
                    const root = document.querySelector('hypeduck-coupang-badge').attachShadow({mode:'open'});
                    const body = document.createElement('body');
                    body.textContent = 'EXTENSION_BODY';
                    root.appendChild(body);
                }""")
                self.assertEqual(page.locator('body').count(),2)
                with self.assertRaisesRegex(Error,'strict mode violation'):
                    page.locator('body').inner_text(timeout=1000)
                for name in ('_scrape_product_page','_scrape_1688_source'):
                    constants = b.find(code,name).co_consts
                    selector = next(v for v in constants if v in ('body','xpath=/html/body'))
                    with self.subTest(scraper=name):
                        self.assertIn('PRODUCT_BODY',page.locator(selector).inner_text(timeout=1000))
                        self.assertEqual(page.locator(selector).count(),1)
                page.locator('hypeduck-coupang-badge').evaluate('(el) => el.remove()')
                self.assertEqual(page.locator('body').inner_text(),page.locator('xpath=/html/body').inner_text())
            finally:
                browser.close()


def live_probe():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp('http://127.0.0.1:9228')
        pages = [page for ctx in browser.contexts for page in ctx.pages if '1072228028593' in page.url]
        if not pages:
            page = browser.contexts[0].new_page()
            page.goto('https://detail.1688.com/offer/1072228028593.html',wait_until='domcontentloaded',timeout=60000)
            pages = [page]
        for page in pages:
            body = page.locator('xpath=/html/body').inner_text(timeout=10000)
            print(json.dumps({'product':'1072228028593','legacy_body_count':page.locator('body').count(),
                              'fixed_body_count':page.locator('xpath=/html/body').count(),'body_chars':len(body),'title':page.title()},ensure_ascii=True))
            if not body.strip():
                raise RuntimeError('Main document text is empty')


if __name__ == '__main__':
    import sys
    if '--live' in sys.argv:
        live_probe()
    else:
        unittest.main(verbosity=2)
