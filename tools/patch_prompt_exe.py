from __future__ import annotations

import argparse
import marshal
import struct
import types
import zlib
from dataclasses import dataclass
from pathlib import Path


MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
COOKIE_FORMAT = "!8sIIii64s"
COOKIE_SIZE = struct.calcsize(COOKIE_FORMAT)
TOC_HEADER_FORMAT = "!iIIIBc"
TOC_HEADER_SIZE = struct.calcsize(TOC_HEADER_FORMAT)
TARGET_SCRIPT = "detail_page_automation_gui"

PATCHED_FUNCTIONS = {
    "_build_gpt_section_plan_request",
    "_build_product_fallback_sections",
    "_chatgpt_section_image_request",
    "_detail_section_common_design_rules",
    "_generate_section_visuals",
    "_is_valid_generated_visual_file",
    "_latest_image_prompt_for_section",
}

OLD_PLAN_CONTRACT = (
    "\n출력 형식은 아래 형식을 섹션 1부터 섹션 10까지 반복해서 지켜줘.\n"
    "각 섹션은 상품별로 다르게 기획하고, 이미지 프롬프트에는 첨부 이미지의 실제 상품 외형/색상/소재/옵션/비율을 유지한다는 조건을 넣어줘.\n\n"
)

NEW_PLAN_CONTRACT = (
    "\n출력 형식은 아래 형식을 섹션 1부터 섹션 10까지 반복해서 지켜줘.\n"
    "각 섹션의 카피는 확인된 상품 사실을 고객이 바로 이해할 수 있는 이점으로 바꾸되, "
    "번역투나 보고서 말투 없이 한국 쇼핑몰에서 자연스럽게 읽히는 문장으로 작성해.\n"
    "'정리했습니다', '보여줍니다', '상상해 보세요', '기준으로' 같은 제작 설명형 문구와 "
    "상품명만 바꾼 템플릿 문장을 쓰지 마.\n"
    "각 이미지 프롬프트에는 첨부 이미지의 실제 상품 외형/색상/소재/옵션/비율 유지 조건과 함께, "
    "해당 상품의 카테고리·용도·소재·구매 상황에서 자연스럽게 도출한 배경 공간, 표면, 조명, 구도, 소품 방향을 구체적으로 적어.\n"
    "같은 상품의 10개 섹션에서 동일한 스튜디오 배경, 동일한 색조, 동일한 카메라 거리, 동일한 소품 구성을 반복하지 말고, "
    "섹션 역할에 맞춰 서로 확실히 다른 장면으로 설계해.\n\n"
)

COMMON_DESIGN_RULES = """전문 상세페이지 디자인·카피 기준:
- 확인된 상품 정보만 사용하고, 기능을 지어내거나 과장하지 말 것.
- 메인 헤드라인은 한 번에 이해되는 짧은 한국어 한 문장으로 쓰고, 서브 카피는 고객이 얻는 이점을 자연스러운 말투로 한 문장만 작성.
- '정리했습니다', '보여줍니다', '상상해 보세요', '기준으로', '쉽게 확인' 같은 제작 설명형·번역투 표현을 쓰지 말 것.
- 한 섹션에는 핵심 메시지 1개만 두고, 본문은 최대 2줄, 불릿은 꼭 필요한 내용만 3개 이하로 구성.
- 제목과 본문에서 같은 말을 반복하지 말고, 가격·후기·원산지·인증처럼 확인되지 않은 정보는 넣지 말 것.
- 폰트는 최대 2종류, 메인 컬러는 제품과 어울리는 2개 중심으로 사용하고 많아도 3개 이하.
- 제목은 64px 이상처럼 분명하게, 서브 카피는 36~40px 기준으로 제목보다 작게 구성.
- 좌우 여백은 최소 40px, 섹션 위아래 여백은 80~100px 기준으로 넉넉하게 확보하고 모든 요소의 기준선을 정확히 맞출 것.
- 배경은 상품의 카테고리, 실제 사용 환경, 소재, 색상, 섹션 역할에서 도출하고 같은 상품의 다른 섹션과 공간·표면·조명·구도·소품을 반복하지 말 것.
- 텍스트는 또렷한 한글로 최소한만 배치하고, 읽기 어려운 장식 글꼴·과도한 카드·배지·템플릿형 문구를 피할 것.
- 이미지 안 문구는 기획된 메인 헤드라인과 서브 카피를 그대로 사용하고, 맞춤법·띄어쓰기를 확인하며 임의 문장을 추가하지 말 것.
- 위 기준은 제작 지시이며 이미지 안에 px 숫자나 규칙 문장을 직접 쓰지 말 것."""

LATEST_IMAGE_PROMPT_SOURCE = Path(__file__).with_name(
    "latest_image_prompt_function.txt"
).read_text(encoding="utf-8")
RUNTIME_SECTION_FIX_SOURCE = Path(__file__).with_name(
    "runtime_section_fix_functions.txt"
).read_text(encoding="utf-8")


@dataclass(frozen=True)
class ArchiveEntry:
    name: str
    compressed_size: int
    uncompressed_size: int
    compressed: int
    type_code: bytes
    raw_data: bytes


@dataclass(frozen=True)
class Archive:
    prefix: bytes
    entries: tuple[ArchiveEntry, ...]
    py_version: int
    python_library: bytes
    tail: bytes


def read_archive(path: Path) -> Archive:
    data = path.read_bytes()
    cookie_position = data.rfind(MAGIC)
    if cookie_position < 0:
        raise RuntimeError("PyInstaller cookie not found")
    magic, package_length, toc_offset, toc_length, py_version, python_library = struct.unpack(
        COOKIE_FORMAT, data[cookie_position : cookie_position + COOKIE_SIZE]
    )
    if magic != MAGIC:
        raise RuntimeError("Invalid PyInstaller cookie")
    tail = data[cookie_position + COOKIE_SIZE :]
    archive_start = len(data) - package_length - len(tail)
    toc_start = archive_start + toc_offset
    position = toc_start
    toc_end = toc_start + toc_length
    entries: list[ArchiveEntry] = []
    while position < toc_end:
        entry_size = struct.unpack("!i", data[position : position + 4])[0]
        fields = struct.unpack(
            f"!IIIBc{entry_size - TOC_HEADER_SIZE}s",
            data[position + 4 : position + entry_size],
        )
        entry_position, compressed_size, uncompressed_size, compressed, type_code, name_bytes = fields
        name = name_bytes.rstrip(b"\0").decode("utf-8")
        raw = data[
            archive_start + entry_position : archive_start + entry_position + compressed_size
        ]
        entries.append(
            ArchiveEntry(name, compressed_size, uncompressed_size, compressed, type_code, raw)
        )
        position += entry_size
    if position != toc_end:
        raise RuntimeError("Invalid PyInstaller TOC length")
    return Archive(data[:archive_start], tuple(entries), py_version, python_library, tail)


def entry_payload(entry: ArchiveEntry) -> bytes:
    return zlib.decompress(entry.raw_data) if entry.compressed else entry.raw_data


def code_function_names(code: types.CodeType) -> set[str]:
    names = {code.co_name}
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            names.update(code_function_names(value))
    return names


def _compiled_function(source: str, name: str) -> types.CodeType:
    module_code = compile(source, "detail_page_automation_gui.py", "exec")
    for value in module_code.co_consts:
        if isinstance(value, types.CodeType) and value.co_name == name:
            return value
    raise RuntimeError(f"Compiled function not found: {name}")


def _replace_code_tree(code: types.CodeType, replacements: dict[str, types.CodeType]) -> types.CodeType:
    new_constants = []
    changed = False
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            if value.co_name in replacements:
                replacement = replacements[value.co_name].replace(
                    co_filename=value.co_filename,
                    co_firstlineno=value.co_firstlineno,
                    co_name=value.co_name,
                    co_qualname=value.co_qualname,
                )
                new_constants.append(replacement)
                changed = True
            else:
                updated = _replace_code_tree(value, replacements)
                new_constants.append(updated)
                changed = changed or updated is not value
        elif code.co_name == "_build_gpt_section_plan_request" and value == OLD_PLAN_CONTRACT:
            new_constants.append(NEW_PLAN_CONTRACT)
            changed = True
        else:
            new_constants.append(value)
    return code.replace(co_consts=tuple(new_constants)) if changed else code


def patch_script_code(code: types.CodeType) -> types.CodeType:
    current_names = code_function_names(code)
    missing = PATCHED_FUNCTIONS - current_names
    if missing:
        raise RuntimeError(f"Required functions missing from current EXE: {sorted(missing)}")
    design_code = compile(
        "def _detail_section_common_design_rules(self):\n    return " + repr(COMMON_DESIGN_RULES),
        "detail_page_automation_gui.py",
        "exec",
    ).co_consts[0]
    latest_code = _compiled_function(LATEST_IMAGE_PROMPT_SOURCE, "_latest_image_prompt_for_section")
    runtime_replacements = {
        name: _compiled_function(RUNTIME_SECTION_FIX_SOURCE, name)
        for name in (
            "_build_product_fallback_sections",
            "_chatgpt_section_image_request",
            "_generate_section_visuals",
            "_is_valid_generated_visual_file",
        )
    }
    patched = _replace_code_tree(
        code,
        {
            "_detail_section_common_design_rules": design_code,
            "_latest_image_prompt_for_section": latest_code,
            **runtime_replacements,
        },
    )
    all_strings = "\n".join(_all_string_constants(patched))
    required = (
        "전문 상세페이지 디자인·카피 기준",
        "이번 섹션 전용 배경 연출",
        "동일한 스튜디오 배경",
        "내부 기본 섹션으로 진행하지 않습니다",
    )
    if any(marker not in all_strings for marker in required):
        raise RuntimeError("Prompt patch validation failed")
    return patched


def _all_string_constants(code: types.CodeType) -> list[str]:
    strings: list[str] = []
    for value in code.co_consts:
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, types.CodeType):
            strings.extend(_all_string_constants(value))
    return strings


def write_archive(archive: Archive, entries: list[ArchiveEntry], output_path: Path) -> None:
    data_chunks: list[bytes] = []
    toc_chunks: list[bytes] = []
    offset = 0
    for entry in entries:
        raw = entry.raw_data
        data_chunks.append(raw)
        name_bytes = entry.name.encode("utf-8") + b"\0"
        entry_size = TOC_HEADER_SIZE + len(name_bytes)
        toc_chunks.append(
            struct.pack(
                f"!iIIIBc{len(name_bytes)}s",
                entry_size,
                offset,
                len(raw),
                entry.uncompressed_size,
                entry.compressed,
                entry.type_code,
                name_bytes,
            )
        )
        offset += len(raw)
    archive_data = b"".join(data_chunks)
    toc_data = b"".join(toc_chunks)
    cookie = struct.pack(
        COOKIE_FORMAT,
        MAGIC,
        len(archive_data) + len(toc_data) + COOKIE_SIZE,
        len(archive_data),
        len(toc_data),
        archive.py_version,
        archive.python_library,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(archive.prefix + archive_data + toc_data + cookie + archive.tail)


def patch_exe(input_path: Path, output_path: Path) -> None:
    archive = read_archive(input_path)
    patched_entries: list[ArchiveEntry] = []
    matched = 0
    for entry in archive.entries:
        if entry.name != TARGET_SCRIPT or entry.type_code != b"s":
            patched_entries.append(entry)
            continue
        matched += 1
        payload = entry_payload(entry)
        code = marshal.loads(payload)
        patched_payload = marshal.dumps(patch_script_code(code))
        raw = zlib.compress(patched_payload, level=9) if entry.compressed else patched_payload
        patched_entries.append(
            ArchiveEntry(
                entry.name,
                len(raw),
                len(patched_payload),
                entry.compressed,
                entry.type_code,
                raw,
            )
        )
    if matched != 1:
        raise RuntimeError(f"Expected one main script entry, found {matched}")
    write_archive(archive, patched_entries, output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_exe", type=Path)
    parser.add_argument("output_exe", type=Path)
    args = parser.parse_args()
    patch_exe(args.input_exe.resolve(), args.output_exe.resolve())
    print(args.output_exe.resolve())


if __name__ == "__main__":
    main()
