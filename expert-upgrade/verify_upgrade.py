from __future__ import annotations

import copy
import hashlib
import json
import marshal
import os
import shutil
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import build_upgrade as b
from tests.test_prompt_exe_patch import direct_function_hashes


def main_code(path):
    return marshal.loads(b.entry_payload(next(e for e in b.read_archive(path).entries if e.name == 'detail_page_automation_gui')))


def hashes(paths):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def all_strings(code):
    for v in code.co_consts:
        if isinstance(v,str):
            yield v
        elif isinstance(v,types.CodeType):
            yield from all_strings(v)


class UpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = main_code(b.BASE)
        cls.after = main_code(b.TARGET)
        cls.completed = Path.home()/'Desktop/상세페이지_자동화_결과/완료된폴더'
        original_config = Path(os.environ['LOCALAPPDATA'])/'SangsapageAutomation'
        cls.protected_paths = [b.BASE,*cls.completed.rglob('*'),*original_config.glob('*')]
        cls.protected_before = hashes(cls.protected_paths)
        cls.module = types.ModuleType('expert_preview_verification')
        cls.module.__file__ = str(b.TARGET.parent/'detail_page_automation_gui.py')
        sys.modules[cls.module.__name__] = cls.module
        exec(cls.after,cls.module.__dict__)
        cls.app = cls.module.QApplication.instance() or cls.module.QApplication([])
        from PySide6.QtGui import QFontDatabase, QFont
        font_id = QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR'])/'Fonts/malgun.ttf'))
        if font_id >= 0:
            cls.app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0],10))
        cls.gui = cls.module.DetailPageGui()
        cls.examples = b.DEST/'프롬프트 검토'
        cls.examples.mkdir(parents=True,exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.gui.market_autosave_timer.stop()
        cls.gui.image_wait_timer.stop()
        cls.gui.deleteLater()
        cls.app.processEvents()
        after = hashes(cls.protected_paths)
        if cls.protected_before != after:
            raise AssertionError('Protected production files changed')
        (b.HERE/'preservation-report.json').write_text(json.dumps({'files_checked':len(after),'unchanged':True},indent=2),encoding='utf-8')

    def test_archive_and_function_boundaries(self):
        before_entries = {e.name:e for e in b.read_archive(b.BASE).entries}
        after_entries = {e.name:e for e in b.read_archive(b.TARGET).entries}
        self.assertEqual(before_entries.keys(),after_entries.keys())
        for name,entry in before_entries.items():
            if name != 'detail_page_automation_gui':
                self.assertEqual(entry.raw_data,after_entries[name].raw_data,name)
        before = direct_function_hashes(self.before)
        after = direct_function_hashes(self.after)
        modified = []
        for name,digest in before.items():
            if after.get(name) == digest:
                continue
            modified.append(name)
            short = name.split('.')[-1]
            if any(m in name for m in (*b.METHODS,'_build_market_panel','_build_gpt_section_plan_request','_detail_section_common_design_rules','_migrate_legacy_config_file','_generate_thumbnail_images','_submit_section_plan_request')):
                continue
            old = b.find(self.before,short)
            new = b.find(self.after,short)
            self.assertIsNotNone(old,name)
            self.assertEqual(old.co_code,new.co_code,name)
            old_text = list(all_strings(old))
            expected = [s.replace('127.0.0.1:9222','127.0.0.1:9228').replace('--remote-debugging-port=9222','--remote-debugging-port=9228').replace('chrome_cdp_profile','chrome_expert_preview_profile') for s in old_text]
            if short in {'_scrape_product_page','_scrape_1688_source'}:
                expected = ['xpath=/html/body' if s == 'body' else s for s in expected]
            self.assertEqual(expected,list(all_strings(new)),name)
        (b.HERE/'function-diff.json').write_text(json.dumps(modified,ensure_ascii=False,indent=2),encoding='utf-8')

    def test_storage_browser_and_credentials_are_isolated(self):
        m = self.module
        self.assertEqual(m.USER_CONFIG_DIR.name,'SangsapageExpertPreview')
        self.assertEqual(m.OUTPUT_DIR.name,'상세페이지_전문가_테스트_결과')
        self.assertEqual(m.MARKET_KEYRING_SERVICE,'detail_page_expert_preview.market')
        self.assertFalse(any('127.0.0.1:9222' in s or '--remote-debugging-port=9222' in s for s in all_strings(self.after)))
        self.assertIn('chrome_expert_preview_profile',list(all_strings(self.after)))
        self.assertNotIn('_write_market_draft_bundle',b.find(self.after,'send_coupang_manual_gpt_prompt').co_names)

    def test_real_completed_products_make_both_market_prompts(self):
        results=[]
        folders = sorted(p for p in self.completed.iterdir() if p.is_dir())
        self.assertTrue(folders, 'No real completed product available for verification')
        for folder in folders:
            fixture = b.HERE/'fixtures'/folder.name
            shutil.copytree(folder,fixture,dirs_exist_ok=True)
            product = self.gui._market_product_from_completed_folder(fixture)
            before = copy.deepcopy((product.source,product.metadata))
            with patch('socket.socket.connect',side_effect=AssertionError('Unexpected network call')):
                draft = self.gui._build_market_draft_bundle(product)
            for platform in ('naver','coupang'):
                prompt = draft[platform+'_chatgpt_prompt']
                self.assertIn(product.product_name,prompt)
                self.assertIn('EXPERT_REGISTRATION_V1',prompt)
                self.assertIn('all_options',prompt)
                self.assertIn('검색 검증 미실행',prompt)
                self.assertIn('20 A/S',prompt)
                self.assertLessEqual(len(prompt),80000)
                (self.examples/(folder.name+'_'+platform+'.txt')).write_text(prompt,encoding='utf-8')
            self.assertEqual(before,(product.source,product.metadata))
            s = product.source
            record = self.module.ProductRecord(
                index=1,url=str(s.get('url','')),secondary_url=str(s.get('secondary_url','')),
                code=product.code,product_name=product.product_name,title=product.product_name,
                category=str(s.get('category','')),price_text=str(s.get('price_text','')),
                options_text=str(s.get('options_text','')),facts=s.get('facts',[]),
                source_text=str(s.get('source_text','')),image_urls=[],source_image_paths=[],output_dir=fixture,
            )
            plan_prompt = self.gui._build_gpt_section_plan_request(record)
            self.assertIn('EXPERT_ART_DIRECTION_V1',plan_prompt)
            self.assertEqual(plan_prompt.count('EXPERT_ART_DIRECTION_V1'),1)
            self.assertIn(product.product_name,plan_prompt)
            self.assertIn('섹션 10',plan_prompt)
            (self.examples/(folder.name+'_detail_plan.txt')).write_text(plan_prompt,encoding='utf-8')
            results.append({'product':folder.name,'naver_chars':len(draft['naver_chatgpt_prompt']),'coupang_chars':len(draft['coupang_chatgpt_prompt'])})
        self.assertEqual(len(results),len(folders))
        (b.HERE/'fixture-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

    def test_all_options_and_sensitive_url_query(self):
        product = types.SimpleNamespace(product_name='검정 장갑',code='fixture',folder=Path('fixture'),source={'url':'https://example.com/item?id=42&token=DO_NOT_SEND','facts':['폴리에스테르']},metadata={})
        items = [{'itemName':f'OPTION_{i:03d}','salePrice':12000+i,'attributes':[{'attributeTypeName':'색상','attributeValueName':f'COLOR_{i}'}]} for i in range(100)]
        payload={'sellerProductName':'장갑','items':items}
        snapshot=copy.deepcopy(payload)
        prompt=self.gui._build_coupang_market_chatgpt_prompt(product,{},payload)
        self.assertIn('OPTION_099',prompt)
        self.assertNotIn('DO_NOT_SEND',prompt)
        self.assertEqual(payload,snapshot)
        long_options={'optionCombinations':[{'optionName1':'검정','optionName2':str(i),'stockQuantity':5} for i in range(100)]}
        naver={'originProduct':{'detailAttribute':{'optionInfo':long_options}}}
        prompt=self.gui._build_naver_market_chatgpt_prompt(product,{},naver)
        self.assertIn('"optionName2": "99"',prompt)
        oversized=copy.deepcopy(product)
        oversized.source['facts']=['x'*81000]
        with self.assertRaisesRegex(ValueError,'80,000'):
            self.gui._build_coupang_market_chatgpt_prompt(oversized,{},payload)

    def test_manual_button_final_prompt_and_outputs(self):
        m = self.module
        product = types.SimpleNamespace(
            code='manual-fixture',product_name='검정 장갑',folder=self.completed/'original-fixture',thumbnail_paths=[],
            source={'url':'https://USERNAME_SECRET@example.com/item?token=SOURCE_SECRET'},
            metadata={'secondary_url':'https://user:PASSWORD_SECRET@example.com/item?signature=SIGNED_SECRET',
                      'source_payloads':[{'url':'https://example.com/item?access_token=PAYLOAD_SECRET'}]},
        )
        draft = {'coupang_chatgpt_prompt':'https://example.com/item?token=BASE_SECRET','coupang_payload':{},'seo_keywords':{}}
        callback = types.FunctionType(b.find(self.after,'send_coupang_manual_gpt_prompt'),m.__dict__,closure=(types.CellType(self.gui),))
        self.gui.market_manual_url_field.setText('https://wing.coupang.com/?token=MANUAL_SECRET')
        self.gui.market_gpt_running = False
        with patch.object(self.gui,'_selected_market_product',return_value=product), \
             patch.object(self.gui,'_persist_market_settings_silent'), \
             patch.object(self.gui,'_build_market_draft_bundle',return_value=draft), \
             patch.object(Path,'mkdir'), \
             patch.object(Path,'write_text',autospec=True) as write, \
             patch.object(self.gui,'_write_json_file') as json_write, \
             patch.object(m.threading,'Thread') as thread:
            callback()
            text_path,prompt = write.call_args.args[:2]
            self.assertTrue(text_path.is_relative_to(m.OUTPUT_DIR))
            self.assertFalse(text_path.is_relative_to(product.folder))
            self.assertNotIn('_secret',prompt.lower())
            self.assertNotIn('_secret',json.dumps(json_write.call_args.args[1]).lower())
            self.assertTrue(json_write.call_args.args[0].is_relative_to(m.OUTPUT_DIR))
            worker = thread.call_args.kwargs['target']
            sent = dict(zip(worker.__code__.co_freevars,(c.cell_contents for c in worker.__closure__)))
            self.assertEqual(sent['manual_prompt'],prompt)
        self.gui.market_gpt_running = False
        with patch.object(self.gui,'_selected_market_product',return_value=product), \
             patch.object(self.gui,'_persist_market_settings_silent'), \
             patch.object(self.gui,'_build_market_draft_bundle',side_effect=ValueError('too large')), \
             patch.object(m.QMessageBox,'warning') as warning, \
             patch.object(m.threading,'Thread') as thread:
            callback()
            warning.assert_called_once()
            thread.assert_not_called()

    def test_detail_contract_preserves_previous_rules_and_gui_renders(self):
        original = types.FunctionType(b.find(self.before,'_detail_section_common_design_rules'),{})(None)
        upgraded = self.gui._detail_section_common_design_rules()
        self.assertTrue(upgraded.startswith(original))
        self.assertIn('EXPERT_ART_DIRECTION_V1',upgraded)
        self.assertIn('확정된 해당 섹션 문구를 그대로',upgraded)
        (self.examples/'상세페이지_추가_디자인_규칙.txt').write_text(upgraded,encoding='utf-8')
        self.gui.resize(1440,1000)
        self.gui.show()
        self.app.processEvents()
        self.assertTrue(self.gui.isVisible())
        self.assertGreater(self.gui.main_tabs.count(),1)
        self.assertTrue(self.gui.grab().save(str(self.examples/'GUI_초기화_검사.png')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
