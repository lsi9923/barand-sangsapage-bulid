from __future__ import annotations

import ast
import hashlib
import inspect
import marshal
import textwrap
import types
import zlib
from pathlib import Path

from tools.patch_prompt_exe import ArchiveEntry, entry_payload, read_archive, write_archive


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "source-recovery" / "detail_page_automation_gui.py"
SCRIPT_NAME = "detail_page_automation_gui"


def find_code(code: types.CodeType, name: str) -> types.CodeType | None:
    if code.co_name == name:
        return code
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            found = find_code(value, name)
            if found is not None:
                return found
    return None


def replace_code_tree(code: types.CodeType, replacements: dict[str, types.CodeType]) -> types.CodeType:
    changed = False
    constants = []
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            replacement = replacements.get(value.co_name)
            if replacement is not None:
                constants.append(
                    replacement.replace(
                        co_name=value.co_name,
                        co_qualname=value.co_qualname,
                        co_filename=value.co_filename,
                        co_firstlineno=value.co_firstlineno,
                    )
                )
                changed = True
            else:
                updated = replace_code_tree(value, replacements)
                constants.append(updated)
                changed = changed or updated is not value
        else:
            constants.append(value)
    return code.replace(co_consts=tuple(constants)) if changed else code


def compiled_function(function) -> types.CodeType:
    source = textwrap.dedent(inspect.getsource(function))
    module_code = compile(source, "detail_page_automation_gui.py", "exec")
    found = find_code(module_code, function.__name__)
    if found is None:
        raise RuntimeError(f"Could not compile {function.__name__}")
    return found


def _patched_is_1688_url_header(self, value: str) -> bool:
    if self._is_url(value):
        return False
    normalized = self._normalize_excel_header(value)
    if not normalized:
        return False
    if any(token in normalized for token in ("이미지", "사진", "썸네일", "thumbnail", "image", "img")):
        return False
    source_tokens = (
        "1688",
        "중국",
        "타오바오",
        "alibaba",
        "도매",
        "공급처",
        "공급자",
        "공급몰",
        "소싱",
        "판매처",
        "원본상품",
        "상품원본",
        "참고상품",
        "source",
        "supplier",
        "wholesale",
        "productsource",
    )
    return any(token in normalized for token in source_tokens)


def _patched_existing_page_for_url(self, context, url: str):
    expected_host = urllib.parse.urlparse(url or "").netloc.lower()
    if not expected_host:
        return None
    expected_root = ".".join(expected_host.split(".")[-2:])
    try:
        pages = list(context.pages)
    except Exception:
        return None
    for page in pages:
        try:
            if page is None or page.is_closed():
                continue
            host = urllib.parse.urlparse(page.url or "").netloc.lower()
            if not host:
                continue
            root = ".".join(host.split(".")[-2:])
            if root == expected_root:
                return page
        except Exception:
            continue
    return None


def _patched_section_planner_page_alive(self, context, page=None):
    self._active_playwright_context = context
    candidates = [page, getattr(self, "_chatgpt_image_generation_page", None)]
    try:
        candidates.extend(reversed(list(context.pages)))
    except Exception:
        pass
    target_page = None
    for candidate in candidates:
        try:
            if candidate is None or candidate.is_closed() or "chatgpt.com" not in (candidate.url or "").lower():
                continue
            if self._is_chatgpt_section_planner_url(candidate.url) and not self._is_chatgpt_encoding_error_page(candidate):
                self._accept_chatgpt_cookies(candidate)
                if not self._page_needs_login(candidate):
                    candidate.bring_to_front()
                    return candidate
            target_page = target_page or candidate
        except Exception:
            continue
    if target_page is None:
        target_page = context.new_page()
    target_page.goto(GPT_URL, wait_until="domcontentloaded", timeout=60000)
    target_page.wait_for_timeout(5000)
    self._accept_chatgpt_cookies(target_page)
    self._dismiss_chatgpt_blocking_modal(target_page)
    self._force_hide_chatgpt_open_sheets(target_page)
    if self._page_needs_login(target_page):
        target_page.bring_to_front()
        raise RuntimeError("ChatGPT 기획용 커스텀 GPT 로그인이 필요합니다.")
    target_page.bring_to_front()
    return target_page


def _patched_extract_general_image_urls(self, page_html: str, page_url: str) -> list[str]:
    if not page_html:
        return []
    raw_urls: list[str] = []
    patterns = (
        r"https?:\\?/\\?/[^'\"<>\s)]+?(?:jpg|jpeg|png|gif|webp|bmp|avif)(?:_[^'\"<>\s)]*)?",
        r"//[^'\"<>\s)]+?(?:jpg|jpeg|png|gif|webp|bmp|avif)(?:_[^'\"<>\s)]*)?",
    )
    for pattern in patterns:
        raw_urls.extend(re.findall(pattern, page_html, flags=re.IGNORECASE))
    image_urls: list[str] = []
    seen: set[str] = set()
    rejected_tokens = (
        "sprite",
        "favicon",
        "icon",
        "avatar",
        "placeholder",
        "captcha",
        "qrcode",
        "qr-code",
        "loading",
    )
    for raw in raw_urls:
        cleaned = html.unescape(raw).replace("\\/", "/").strip()
        cleaned = urllib.parse.unquote(cleaned).rstrip("\\\"' ),;")
        if cleaned.startswith("//"):
            cleaned = "https:" + cleaned
        cleaned = urllib.parse.urljoin(page_url, cleaned)
        parsed = urllib.parse.urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        lower = cleaned.lower()
        if any(token in lower for token in rejected_tokens):
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        image_urls.append(cleaned)
    return image_urls


def _patched_rank_1688_image_candidates(
    self,
    image_candidates: list[dict[str, str | int]],
    image_urls: list[str],
) -> list[dict[str, str | int]]:
    records: list[dict[str, str | int]] = []
    rejected_tokens = (
        "sprite",
        "favicon",
        "icon",
        "avatar",
        "placeholder",
        "captcha",
        "qrcode",
        "qr-code",
        "loading",
    )

    def usable_source(src: str) -> bool:
        if not src:
            return False
        try:
            parsed = urllib.parse.urlparse(src)
        except Exception:
            return False
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        lower = src.lower()
        return not any(token in lower for token in rejected_tokens)

    for item in image_candidates:
        src = str(item.get("src") or "").strip()
        if not usable_source(src):
            continue
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        client_width = int(item.get("client_width") or 0)
        client_height = int(item.get("client_height") or 0)
        if max(width, client_width) < 240 or max(height, client_height) < 240:
            continue
        record = dict(item)
        record["role"] = "1688"
        records.append(record)
    for src in image_urls:
        src = str(src or "").strip()
        if not usable_source(src):
            continue
        records.append(
            {
                "src": src,
                "alt": "source product image",
                "width": 0,
                "height": 0,
                "client_width": 0,
                "client_height": 0,
                "top": 999999,
                "parent_chain": "",
                "role": "1688",
            }
        )
    deduped: list[dict[str, str | int]] = []
    seen: set[str] = set()
    for item in sorted(
        records,
        key=lambda record: (
            int(record.get("top") or 999999),
            -max(int(record.get("width") or 0), int(record.get("client_width") or 0))
            * max(int(record.get("height") or 0), int(record.get("client_height") or 0)),
        ),
    ):
        src = str(item.get("src") or "")
        if not src or src in seen:
            continue
        seen.add(src)
        deduped.append(item)
    return deduped[:18]


def _patched_extract_detail_image_urls(self, page_html: str, page_url: str) -> list[str]:
    if not page_html:
        return []
    raw_urls: list[str] = []
    patterns = (
        r"https?:\\?/\\?/[^'\"<>\s)]+?\.(?:jpg|jpeg|png|gif|webp|bmp|avif)(?:\?[^'\"<>\s)]*)?",
        r"//[^'\"<>\s)]+?\.(?:jpg|jpeg|png|gif|webp|bmp|avif)(?:\?[^'\"<>\s)]*)?",
        r"https?:\\?/\\?/[^'\"<>\s)]+?/upload/item/[^'\"<>\s)]+",
        r"//[^'\"<>\s)]+?/upload/item/[^'\"<>\s)]+",
    )
    for pattern in patterns:
        raw_urls.extend(re.findall(pattern, page_html, flags=re.IGNORECASE))
    rejected_tokens = (
        "sprite",
        "favicon",
        "avatar",
        "placeholder",
        "captcha",
        "qrcode",
        "qr-code",
        "loading",
        "icon",
        "button",
        "notice",
        "delivery",
        "return",
        "cscenter",
        "membership",
        "review",
    )
    detail_urls: list[str] = []
    seen: set[str] = set()
    for raw in raw_urls:
        cleaned = html.unescape(raw).replace("\\/", "/").strip()
        cleaned = urllib.parse.unquote(cleaned).rstrip("\\\"' ),;")
        if cleaned.startswith("//"):
            cleaned = "https:" + cleaned
        cleaned = urllib.parse.urljoin(page_url, cleaned)
        parsed = urllib.parse.urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        lower = cleaned.lower()
        if any(token in lower for token in rejected_tokens):
            continue
        path = parsed.path.lower()
        if not re.search(r"\.(?:jpg|jpeg|png|gif|webp|bmp|avif)$", path) and "/upload/item/" not in path:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        detail_urls.append(cleaned)
    return detail_urls


def _patched_product_detail_image_candidate(self, record: dict[str, str | int]) -> bool:
    src = str(record.get("src") or "")
    src_lower = src.lower()
    chain = str(record.get("parent_chain") or "").lower()
    if self._is_ownerclan_ui_image_src(src) or self._looks_like_recommendation_image(record):
        return False
    if any(
        marker in src_lower or marker in chain
        for marker in (
            "sprite",
            "favicon",
            "avatar",
            "placeholder",
            "captcha",
            "qrcode",
            "qr-code",
            "loading",
            "notice",
            "delivery",
            "return",
            "cscenter",
            "membership",
            "banner",
            "review",
        )
    ):
        return False
    width = int(record.get("width") or 0)
    height = int(record.get("height") or 0)
    client_width = int(record.get("client_width") or 0)
    client_height = int(record.get("client_height") or 0)
    if max(width, client_width) < 500 or max(height, client_height) < 300:
        return False
    if int(record.get("top") or 0) > 9000:
        return False
    return True


def _patched_product_thumbnail_candidate(self, record: dict[str, str | int]) -> bool:
    src = str(record.get("src") or "")
    chain = str(record.get("parent_chain") or "").lower()
    width = int(record.get("width") or 0)
    height = int(record.get("height") or 0)
    client_width = int(record.get("client_width") or 0)
    client_height = int(record.get("client_height") or 0)
    top = int(record.get("top") or 0)
    lower = src.lower()
    if self._is_ownerclan_ui_image_src(src) or self._looks_like_recommendation_image(record):
        return False
    if any(
        marker in lower or marker in chain
        for marker in (
            "sprite",
            "favicon",
            "avatar",
            "placeholder",
            "captcha",
            "qrcode",
            "qr-code",
            "loading",
            "banner",
            "review",
            "membership",
            "notice",
            "delivery",
            "return",
            "cscenter",
        )
    ):
        return False
    if max(width, client_width) < 320 or max(height, client_height) < 320:
        return False
    if max(height, client_height) / max(1, max(width, client_width)) > 1.8:
        return False
    if top > 1800 and not any(marker in chain for marker in ("showimage", "product_information", "product", "goods", "item")):
        return False
    visible_area = client_width * client_height
    if visible_area == 0 and not any(marker in chain for marker in ("showimage", "product_information", "product", "goods", "item")) and top > 0:
        return False
    return True


def _patched_primary_product_image_candidate(self, record: dict[str, str | int]) -> bool:
    src = str(record.get("src") or "")
    src_lower = src.lower()
    chain = str(record.get("parent_chain") or "").lower()
    if self._is_ownerclan_ui_image_src(src) or self._looks_like_recommendation_image(record):
        return False
    if any(
        marker in src_lower or marker in chain
        for marker in (
            "sprite",
            "favicon",
            "avatar",
            "placeholder",
            "captcha",
            "qrcode",
            "qr-code",
            "loading",
            "banner",
            "review",
            "membership",
            "notice",
            "delivery",
            "return",
            "cscenter",
        )
    ):
        return False
    width = int(record.get("width") or 0)
    height = int(record.get("height") or 0)
    client_width = int(record.get("client_width") or 0)
    client_height = int(record.get("client_height") or 0)
    top = int(record.get("top") or 0)
    if top >= 1600:
        return False
    if "lthumb" in chain or "mainthumb" in chain:
        return max(width, client_width) >= 300 and max(height, client_height) >= 300
    return (
        max(width, client_width) >= 300
        and max(height, client_height) >= 300
        and top < 1200
    )


def _patched_source_payload_usable(self, payload: dict[str, object]) -> bool:
    text = re.sub(r"\s+", " ", str(payload.get("text", "") or "")).strip()
    title = str(payload.get("title", "") or "")
    downloaded_images = [
        item
        for item in payload.get("downloaded_images", [])
        if isinstance(item, dict)
        and str(item.get("role", "")).strip() != "page_capture"
        and self._is_valid_image_file(Path(str(item.get("local_path", ""))))
    ]
    if downloaded_images:
        return True
    source_paths = [
        Path(str(value))
        for value in payload.get("source_image_paths", [])
        if str(value).strip() and "page_capture" not in str(value).lower()
    ]
    if any(self._is_valid_image_file(path) for path in source_paths):
        return True
    image_urls = [str(src).strip() for src in payload.get("image_urls", []) if str(src).strip()]
    if len(image_urls) < 2 or len(text) < 200:
        return False
    product_signal_text = f"{title} {text}".lower()
    blocked_signals = (
        "login",
        "sign in",
        "signin",
        "captcha",
        "验证",
        "登录",
        "请登录",
        "安全验证",
    )
    if any(signal in product_signal_text for signal in blocked_signals) and len(image_urls) < 4:
        return False
    product_signals = (
        "1688",
        "阿里巴巴",
        "价格",
        "商品",
        "详情",
        "规格",
        "颜色",
        "采购",
        "起批",
        "offer",
    )
    return sum(1 for signal in product_signals if signal.lower() in product_signal_text) >= 2


def source_function_node(name: str) -> ast.FunctionDef:
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise RuntimeError(f"Source function not found: {name}")


def compiled_source_function(name: str) -> types.CodeType:
    node = source_function_node(name)
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), node],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    code = compile(module, "detail_page_automation_gui.py", "exec")
    found = find_code(code, name)
    if found is None:
        raise RuntimeError(f"Could not compile source function {name}")
    return found


def lifecycle_retry_submit_code() -> types.CodeType:
    return compiled_source_function("_submit_section_plan_request")


def patch_exe(input_path: Path, output_path: Path) -> list[str]:
    source_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    archive = read_archive(input_path)
    replacements = {
        "_is_1688_url_header": compiled_function(_patched_is_1688_url_header),
        "_existing_page_for_url": compiled_function(_patched_existing_page_for_url),
        "_ensure_chatgpt_section_planner_page_alive": compiled_function(_patched_section_planner_page_alive),
        "_extract_general_image_urls": compiled_function(_patched_extract_general_image_urls),
        "_extract_detail_image_urls": compiled_function(_patched_extract_detail_image_urls),
        "_is_product_detail_image_candidate": compiled_function(_patched_product_detail_image_candidate),
        "_is_product_thumbnail_candidate": compiled_function(_patched_product_thumbnail_candidate),
        "_is_primary_product_image_candidate": compiled_function(_patched_primary_product_image_candidate),
        "_rank_1688_image_candidates": compiled_function(_patched_rank_1688_image_candidates),
        "_is_1688_source_payload_usable": compiled_function(_patched_source_payload_usable),
        "_submit_section_plan_request": lifecycle_retry_submit_code(),
    }
    entries: list[ArchiveEntry] = []
    changed_entries = 0
    for entry in archive.entries:
        if entry.name != SCRIPT_NAME or entry.type_code != b"s":
            entries.append(entry)
            continue
        changed_entries += 1
        module_code = marshal.loads(entry_payload(entry))
        patched = replace_code_tree(module_code, replacements)
        payload = marshal.dumps(patched)
        raw = zlib.compress(payload, level=9) if entry.compressed else payload
        entries.append(ArchiveEntry(entry.name, len(raw), len(payload), entry.compressed, entry.type_code, raw))
    if changed_entries != 1:
        raise RuntimeError(f"Expected one main script entry, found {changed_entries}")
    write_archive(archive, entries, output_path)
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != source_hash:
        raise RuntimeError("The source EXE was modified")
    return sorted(replacements)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_exe",
        nargs="?",
        type=Path,
        default=Path.home() / "Desktop" / "상세페이지 자동화 GUI - 같은탭_썸네일보강_작업제어.exe",
    )
    parser.add_argument(
        "output_exe",
        nargs="?",
        type=Path,
        default=Path.home() / "Desktop" / "상세페이지 자동화 GUI - 같은탭_렌더보강.exe",
    )
    args = parser.parse_args()
    changed = patch_exe(args.input_exe.resolve(), args.output_exe.resolve())
    print(args.output_exe.resolve())
    print("patched:", ", ".join(changed))


if __name__ == "__main__":
    main()
