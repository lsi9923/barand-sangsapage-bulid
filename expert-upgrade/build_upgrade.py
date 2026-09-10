from __future__ import annotations

import ast
import dis
import hashlib
import json
import marshal
import os
import sys
import textwrap
import types
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from tools.patch_prompt_exe import ArchiveEntry, entry_payload, read_archive, write_archive

BASE = Path.home() / 'Desktop' / '상세페이지 자동화 GUI - 로고상품 프롬프트폴더.exe'
DEST = Path.home() / 'Desktop' / '상세페이지 전문가 업그레이드 - 테스트'
TARGET = Path(os.environ.get('EXPERT_PREVIEW_EXE',str(DEST / '상세페이지 전문가 업그레이드 - 테스트.exe')))
DESIGN = (HERE / 'detail-design.txt').read_text(encoding='utf-8')
MARKET = (HERE / 'registration-rules.txt').read_text(encoding='utf-8')
METHODS = {'_build_naver_market_chatgpt_prompt', '_build_coupang_market_chatgpt_prompt'}


def find(code, name):
    if code.co_name == name:
        return code
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            found = find(value, name)
            if found is not None:
                return found
    return None


def semantic(code):
    instructions = [i for i in dis.get_instructions(code) if i.opname != 'PUSH_NULL']
    offsets = {i.offset:n for n,i in enumerate(instructions)}
    normalized = []
    for ins in instructions:
        arg = ins.argval
        if ins.opcode in dis.hasjabs or ins.opcode in dis.hasjrel:
            target = next(i.offset for i in instructions if i.offset >= arg)
            arg = offsets[target]
        if isinstance(arg, types.CodeType):
            arg = semantic(arg)
        normalized.append(('LOAD_ATTR' if ins.opname == 'LOAD_METHOD' else ins.opname, arg))
    return (code.co_argcount,code.co_names,tuple(normalized))


def market_method(original):
    source = (ROOT / 'source-recovery/detail_page_automation_gui.py').read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == original.co_name)
    method = ast.unparse(node)
    baseline = find(compile(method, original.co_filename, 'exec'), original.co_name)
    if semantic(baseline) != semantic(original):
        raise RuntimeError(f'Recovered method differs from live EXE: {original.co_name}')
    method = method.replace('return f', 'base_prompt = f', 1)
    method = method.replace('json.dumps(option_info, ensure_ascii=False)[:2500]', 'json.dumps(option_info, ensure_ascii=False)')
    platform = 'naver' if 'naver' in original.co_name else 'coupang'
    extra = (HERE / 'market-evidence-function.txt').read_text(encoding='utf-8')
    method += '\n' + textwrap.indent(extra.replace('PLATFORM_LITERAL', repr(platform)).replace('RULES_LITERAL', repr(MARKET)), '    ')
    return find(compile(method, original.co_filename, 'exec'), original.co_name).replace(co_qualname=original.co_qualname)


def manual_method(original):
    source = (ROOT/'tools/market_manual_gpt_block.txt').read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse('def outer(self):\n'+source)) if isinstance(n,ast.FunctionDef) and n.name == original.co_name)
    method = ast.unparse(node)

    def compile_nested(body):
        return find(compile('def outer(self):\n'+textwrap.indent(body,'    '),original.co_filename,'exec'),original.co_name)

    if semantic(compile_nested(method)) != semantic(original):
        raise RuntimeError('Recovered manual handler differs from live EXE')
    safety = (HERE/'manual-safety.txt').read_text(encoding='utf-8')
    method = method.replace('\n    product =', '\n'+textwrap.indent(safety,'    ')+'\n    product =',1)
    method = method.replace("host = parsed.netloc.lower().split(':', 1)[0]", "host = (parsed.hostname or '').lower()",1)
    method = method.replace('draft = self._write_market_draft_bundle(product)',
        "try:\n        draft = self._build_market_draft_bundle(product)\n    except Exception as exc:\n        QMessageBox.warning(self, '초안 생성 실패', str(exc))\n        return",1)
    method = method.replace('evidence_json = json.dumps(evidence,', 'evidence = sanitize_evidence(evidence)\n    evidence_json = json.dumps(evidence,',1)
    method = method.replace("market_dir = product.folder / 'market'",
        "manual_prompt = sanitize_text(manual_prompt)\n    if len(manual_prompt) > 80000:\n        QMessageBox.warning(self, '초안 길이 초과', '전체 요청이 80,000자를 초과합니다. 옵션을 잘라 보내지 않았습니다.')\n        return\n    market_dir = OUTPUT_DIR / 'market_prompt_reviews' / sha256(str(product.folder.resolve()).encode('utf-8')).hexdigest()[:16]",1)
    return compile_nested(method).replace(co_qualname=original.co_qualname)


def thumbnail_method(original):
    source = (ROOT/'source-recovery/detail_page_automation_gui.py').read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name == original.co_name)
    baseline = find(compile(ast.unparse(node),original.co_filename,'exec'),original.co_name)
    if semantic(baseline) != semantic(original):
        raise RuntimeError('Recovered thumbnail generator differs from live EXE')
    node.body = [n for n in node.body if not (
        isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr == '_wait_for_gpt_idle'
        or isinstance(n,ast.For) and ast.unparse(n.iter) == "prompt_dir.glob('thumbnail_*')"
    )]
    method = ast.unparse(node)

    def replace_once(old,new):
        nonlocal method
        if method.count(old) != 1:
            raise RuntimeError('Thumbnail patch anchor mismatch: '+old[:70])
        method = method.replace(old,new,1)

    helpers = """def retryable(exc):
    if isinstance(exc, (AutomationStopRequested, AutomationSkipRequested)) or self._is_browser_disconnected_error(exc):
        return False
    message = str(exc)
    return self._should_retry_chatgpt_image_request(exc) or any(marker in message for marker in (
        '이미지 생성 결과를 제한 시간 안에 찾지 못했습니다',
        '이전 답변 생성이 끝나지 않아',
        '이미지 응답을 시작하지 않았습니다',
    ))

def record_unhandled(index, attempt, exc):
    log = product.output_dir / 'thumbnail_prompts' / f'thumbnail_{index:02d}_retry.log'
    with log.open('a', encoding='utf-8') as stream:
        stream.write(f'[{now_stamp()}] attempt {attempt}: {type(exc).__name__}: {exc}\\n')

def latest_user_turn_id():
    return page.evaluate('''() => {
        const users = [...document.querySelectorAll('[data-turn="user"], [data-message-author-role="user"]')];
        const user = users[users.length - 1];
        const turn = user?.closest('[data-testid^="conversation-turn-"], article') || user;
        return turn?.getAttribute('data-testid') || turn?.id || user?.getAttribute('data-message-id') || '';
    }''')

def wait_for_acknowledgment(before_id):
    for check in range(16):
        self._raise_if_user_requested_stop_or_skip()
        current = latest_user_turn_id()
        if current and current != before_id:
            return True
        if check < 15:
            page.wait_for_timeout(1000)
    return False
"""
    replace_once('\n    resume_start =','\n'+textwrap.indent(helpers,'    ')+'\n    resume_start =')
    replace_once('candidate: dict | None = None','candidate: dict | None = None\n            user_turn_before = latest_user_turn_id()')
    send = 'self._send_prompt_to_gpt_page(page, request_to_send, attachment_paths=attachment_paths, image_mode=False)'
    replace_once(send,
        'self._wait_for_gpt_idle(page, timeout_seconds=CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS)\n'
        '                previous_signatures = self._assistant_image_signatures(page)\n'
        '                previous_stop_count = self._chatgpt_stop_marker_count(page)\n'
        '                previous_text, _ = self._latest_gpt_text(page)\n'
        '                user_turn_before = latest_user_turn_id()\n'
        '                '+send+'\n'
        '                acknowledged = wait_for_acknowledgment(user_turn_before)\n'
        '                if not acknowledged:\n'
        "                    raise RuntimeError('ChatGPT 전송 후에도 프롬프트가 입력창에 남아 있습니다.')")
    anchor = '                try:\n                    candidate = self._wait_for_chatgpt_generated_image('
    if method.count(anchor) != 2:
        raise RuntimeError('Expected send recovery and ordinary image wait')
    method = method.replace(anchor,
        '                try:\n                    if not wait_for_acknowledgment(user_turn_before):\n                        raise send_exc\n                    candidate = self._wait_for_chatgpt_generated_image(',1)
    replace_once('if not self._should_retry_chatgpt_image_request(send_exc):\n                        raise',
        'if not retryable(send_exc):\n                        record_unhandled(thumbnail_index, attempt, send_exc)\n                        raise')
    replace_once('if not self._should_retry_chatgpt_image_request(exc):\n                        raise',
        'if not retryable(exc):\n                        record_unhandled(thumbnail_index, attempt, exc)\n                        raise')
    replace_once('회 실패 후 현재 상품 썸네일 생성을 중단합니다.', '회 실패 후 다음 썸네일을 시도합니다.')
    replace_once("raise ThumbnailGenerationFailed(f'썸네일 {thumbnail_index} 생성 실패: {failure_text}')",'continue')
    return find(compile(method,original.co_filename,'exec'),original.co_name).replace(co_qualname=original.co_qualname)


def plan_submission_method(original):
    source = (ROOT/'source-recovery/detail_page_automation_gui.py').read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name == original.co_name)
    method = ast.unparse(node)
    baseline = find(compile(method,original.co_filename,'exec'),original.co_name)
    if semantic(baseline) != semantic(original):
        raise RuntimeError('Recovered plan submission differs from live EXE')
    anchor = '    self._send_prompt_to_gpt_page(page, prompt.strip(), attachment_paths=attachment_paths or [])'
    if method.count(anchor) != 1:
        raise RuntimeError('Plan send anchor mismatch')
    replacement = '''    user_selector = "() => [...document.querySelectorAll('[data-turn=\\\"user\\\"], [data-message-author-role=\\\"user\\\"]')].map(user => { const turn = user.closest('[data-testid^=\\\"conversation-turn-\\\"], article') || user; return turn.getAttribute('data-testid') || turn.id || user.getAttribute('data-message-id') || ''; }).filter(Boolean)"
    before_user_ids = set(page.evaluate(user_selector))
    try:
        self._send_prompt_to_gpt_page(page, prompt.strip(), attachment_paths=attachment_paths or [])
    except Exception as send_exc:
        if not self._should_retry_chatgpt_image_request(send_exc):
            raise
        for check in range(16):
            self._raise_if_user_requested_stop_or_skip()
            if set(page.evaluate(user_selector)) - before_user_ids:
                break
            if check == 15:
                raise send_exc
            page.wait_for_timeout(1000)'''
    method = method.replace(anchor,replacement,1)
    return find(compile(method,original.co_filename,'exec'),original.co_name).replace(co_qualname=original.co_qualname)


def browser_path_method(original):
    source = (ROOT / 'source-recovery/detail_page_automation_gui.py').read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == original.co_name)
    baseline = find(compile(ast.unparse(node), original.co_filename, 'exec'), original.co_name)
    if semantic(baseline) != semantic(original):
        raise RuntimeError('Browser executable lookup differs from live EXE')
    lines = [
        'def _system_browser_executable_path(self) -> Path | None:',
        '    local_app_data = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))',
        '    candidates = [',
        '        Path(r"C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"),',
        '        Path(r"C:\\\\Program Files (x86)\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"),',
        '        local_app_data / "Google" / "Chrome" / "Application" / "chrome.exe",',
        '        Path(r"C:\\\\Program Files\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe"),',
        '        Path(r"C:\\\\Program Files (x86)\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe"),',
        '        local_app_data / "Microsoft" / "Edge" / "Application" / "msedge.exe",',
        '    ]',
        '    return next((path for path in candidates if path.exists()), None)',
    ]
    return find(compile('\n'.join(lines), original.co_filename, 'exec'), original.co_name).replace(co_qualname=original.co_qualname)


def cdp_browser_method(original):
    source = (ROOT / 'source-recovery/detail_page_automation_gui.py').read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == original.co_name)
    baseline = find(compile(ast.unparse(node), original.co_filename, 'exec'), original.co_name)
    if semantic(baseline) != semantic(original):
        raise RuntimeError('CDP browser launcher differs from live EXE')
    lines = [
        'def _ensure_cdp_browser(self) -> None:',
        '    if self._is_cdp_alive():',
        '        return',
        '    browser_path = self._system_browser_executable_path()',
        '    if not browser_path:',
        '        raise RuntimeError("Chrome 또는 Edge 실행 파일을 찾지 못했습니다.")',
        '    profile_dir = USER_CONFIG_DIR / "automation_browser_profile"',
        '    profile_dir.mkdir(parents=True, exist_ok=True)',
        '    subprocess.Popen([str(browser_path), "--remote-debugging-port=9228", f"--user-data-dir={profile_dir}", "--no-first-run", "--no-default-browser-check", GPT_URL], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)',
        '    for _ in range(20):',
        '        if self._is_cdp_alive():',
        '            return',
        '        time.sleep(0.5)',
        '    raise RuntimeError("자동화 브라우저 CDP 연결을 열지 못했습니다.")',
    ]
    return find(compile('\n'.join(lines), original.co_filename, 'exec'), original.co_name).replace(co_qualname=original.co_qualname)


def transform(code, changed):
    if code.co_name == '_system_browser_executable_path':
        changed.append(code.co_name)
        return browser_path_method(code)
    if code.co_name == '_ensure_cdp_browser':
        changed.append(code.co_name)
        return cdp_browser_method(code)
    if code.co_name == '_submit_section_plan_request':
        changed.append(code.co_name)
        return plan_submission_method(code)
    if code.co_name == '_generate_thumbnail_images':
        changed.append(code.co_name)
        return thumbnail_method(code)
    if code.co_name == 'send_coupang_manual_gpt_prompt':
        code = manual_method(code)
    if code.co_name == '_migrate_legacy_config_file':
        replacement = find(compile('def _migrate_legacy_config_file(self):\n    return\n', code.co_filename, 'exec'), code.co_name)
        changed.append(code.co_name)
        return replacement.replace(co_qualname=code.co_qualname)
    if code.co_name in METHODS:
        changed.append(code.co_name)
        return market_method(code)
    values = list(code.co_consts)
    for i, value in enumerate(values):
        if isinstance(value, types.CodeType):
            values[i] = transform(value, changed)
        elif isinstance(value,str):
            updated = value.replace('127.0.0.1:9222','127.0.0.1:9228').replace('--remote-debugging-port=9222','--remote-debugging-port=9228')
            if value == 'chrome_cdp_profile':
                updated = 'chrome_expert_preview_profile'
            values[i] = updated
    if code.co_name in {'_scrape_product_page','_scrape_1688_source'}:
        if values.count('body') != 1:
            raise RuntimeError('Product body selector anchor mismatch')
        values[values.index('body')] = 'xpath=/html/body'
        changed.append(code.co_name)
    if code.co_name == '_detail_section_common_design_rules':
        matches = [i for i, v in enumerate(values) if isinstance(v, str) and v.startswith('전문 상세페이지 디자인·카피 기준:')]
        if len(matches) != 1:
            raise RuntimeError('Design contract anchor mismatch')
        values[matches[0]] += DESIGN
        changed.append(code.co_name)
    if code.co_name == '_build_gpt_section_plan_request':
        matches = [i for i,v in enumerate(values) if isinstance(v,str) and v.startswith('\n출력 형식은 아래 형식을 섹션 1부터')]
        if len(matches) != 1:
            raise RuntimeError('Plan contract anchor mismatch')
        values[matches[0]] += '\n기존 섹션 1~10 출력 형식과 제목/메인 헤드라인/서브 카피/본문/이미지 프롬프트 필드는 그대로 유지한다. 디자인 판단을 별도 서문으로 출력하지 말고 해당 이미지 프롬프트에 반영한다.\n'
        changed.append(code.co_name)
    if code.co_name == 'send_coupang_manual_gpt_prompt':
        names = tuple('_build_market_draft_bundle' if n == '_write_market_draft_bundle' else n for n in code.co_names)
        old = "- 원본명이나 이미지에 타사 브랜드·차종·캐릭터·작품명·로고가 있으면 이를 숨기거나 '끄롱마제' 제품으로 바꾸지 않는다. 정품/판매권 근거가 없으면 `등록 보류 - 권리 확인 필요`로 판정한다."
        new = "- 타사 제조 브랜드와 확인된 호환 차종을 구분한다. 타사 상품을 자사 제조품으로 바꾸지 않는다. 차종 언급만으로 등록 보류하지 않는다. 권리 근거가 필요한 상품은 확인할 내용을 적고 판매 가능/불가를 단정하지 않는다."
        matches = [i for i,v in enumerate(values) if isinstance(v,str) and old in v]
        if len(matches) != 1:
            raise RuntimeError('Manual prompt contract anchor mismatch')
        values[matches[0]] = values[matches[0]].replace(old, new).replace(
            '- 일반 상품은 상품명을 \'끄롱마제\'로 시작하고 판매처명·최저가·무료배송 같은 광고 문구를 제거한다.',
            '- 자기 브랜드로 확인된 상품은 끄롱마제를 사용한다. 확인된 호환 모델은 제조 브랜드와 구분해서 쓴다. 판매처·최저가·무료배송 같은 광고 문구를 상품명에서 제거한다.'
        ).replace('각 항목은 바로 복사할 수 있는 실제 값부터 보여준다.', '위 기존 출력 목록은 요약으로 사용하고, 앞서 주어진 EXPERT_REGISTRATION_V1의 20개 영역 입력표를 본문으로 완성한다. 각 항목은 바로 복사할 수 있는 실제 값부터 보여준다.')
        changed.append(code.co_name)
        return code.replace(co_consts=tuple(values), co_names=names)
    if code.co_name == '<module>':
        replacements = {
            '상세페이지 자동화 GUI': '상세페이지 전문가 업그레이드 - 테스트',
            'SangsapageAutomation': 'SangsapageExpertPreview',
            '상세페이지_자동화_결과': '상세페이지_전문가_테스트_결과',
            'detail_page_automation_gui.chatgpt': 'detail_page_expert_preview.chatgpt',
            'detail_page_automation_gui.market': 'detail_page_expert_preview.market',
        }
        for old,new in replacements.items():
            if values.count(old) != 1:
                raise RuntimeError(f'Isolation anchor mismatch: {old}')
            values[values.index(old)] = new
    return code.replace(co_consts=tuple(values))


def build():
    before = hashlib.sha256(BASE.read_bytes()).hexdigest()
    archive = read_archive(BASE)
    if archive.py_version != sys.version_info.major * 100 + sys.version_info.minor:
        raise RuntimeError('Python bytecode version mismatch')
    entries, changed = [], []
    for entry in archive.entries:
        if entry.name == 'detail_page_automation_gui' and entry.type_code == b's':
            raw = marshal.dumps(transform(marshal.loads(entry_payload(entry)), changed))
            packed = zlib.compress(raw, 9) if entry.compressed else raw
            entry = ArchiveEntry(entry.name, len(packed), len(raw), entry.compressed, entry.type_code, packed)
        entries.append(entry)
    expected = METHODS | {'_detail_section_common_design_rules','_build_gpt_section_plan_request','send_coupang_manual_gpt_prompt','_migrate_legacy_config_file','_scrape_product_page','_scrape_1688_source','_generate_thumbnail_images','_submit_section_plan_request','_system_browser_executable_path','_ensure_cdp_browser'}
    if set(changed) != expected or len(changed) != len(expected):
        raise RuntimeError(f'Unexpected changed methods: {changed}')
    DEST.mkdir(parents=True, exist_ok=True)
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    if TARGET.resolve() == BASE.resolve():
        raise RuntimeError('Candidate target must differ from original EXE')
    write_archive(archive, entries, TARGET)
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != before:
        raise RuntimeError('Original EXE changed')
    report = {'base':str(BASE),'base_sha256':before,'target':str(TARGET),'target_sha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),'changed_methods':changed,'isolated_config':'SangsapageExpertPreview','isolated_output':'상세페이지_전문가_테스트_결과'}
    (HERE/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    build()
