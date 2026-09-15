import marshal
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

import build_upgrade as b


class ThumbnailFlowTests(unittest.TestCase):
    def run_flow(self,always_fail_second=False,fail_index=2,acknowledged_timeout=False,existing_first=False,delayed_ack=False):
        entry = next(e for e in b.read_archive(b.TARGET).entries if e.name == 'detail_page_automation_gui')
        code = b.find(marshal.loads(b.entry_payload(entry)),'_generate_thumbnail_images')
        attempts = {}
        state = {'index':0,'ack':0,'pending':False}
        runtime_error = type('ThumbnailGenerationFailed',(RuntimeError,),{})
        env = {'Path':Path,'re':__import__('re'),'now_stamp':lambda:'TEST','REQUIRED_THUMBNAIL_IMAGE_COUNT':5,
               'CHATGPT_THUMBNAIL_IMAGE_RETRY_LIMIT':3,'CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS':210,
               'CHATGPT_THUMBNAIL_ACTIVE_WAIT_EXTENSION_SECONDS':180,
               'CHATGPT_IMAGE_WAIT_TIMEOUT_SECONDS':180,'CHATGPT_WEB_IMAGE_MODEL':'web',
               'ThumbnailResult':lambda **kw:types.SimpleNamespace(**kw),'ThumbnailGenerationFailed':runtime_error,
               'AutomationStopRequested':type('AutomationStopRequested',(RuntimeError,),{}),
               'AutomationSkipRequested':type('AutomationSkipRequested',(RuntimeError,),{})}
        owner = types.SimpleNamespace(automation_signals=types.SimpleNamespace(status=Mock(),task_status=Mock(),result=Mock()))
        for name in ('_accept_chatgpt_cookies','_wait_for_gpt_idle','_raise_if_user_requested_stop_or_skip','_reload_chatgpt_for_thumbnail_image_retry','_normalize_thumbnail_image'):
            setattr(owner,name,Mock())
        for name in ('_page_needs_login','_image_matches_reference_sources','_image_duplicates_existing_paths','_image_duplicates_other_product_thumbnail','_is_browser_disconnected_error'):
            setattr(owner,name,lambda *args:False)
        owner._is_valid_thumbnail_file = lambda path:path.is_file()
        owner._chatgpt_thumbnail_image_request = lambda product,sections,index,retry_variant=0:str(index)
        owner._assistant_image_signatures = lambda page:set()
        owner._chatgpt_stop_marker_count = lambda page:0
        owner._latest_gpt_text = lambda page:('old image',True)
        owner._thumbnail_reference_attachment_paths = lambda *args:[]
        owner._chatgpt_user_message_count = lambda page:7
        owner._composer_contains_text = lambda *args:state['pending']
        owner._latest_user_message_matches_prompt = lambda *args:not state['pending']
        owner._should_retry_chatgpt_image_request = lambda exc:'전송 후에도' in str(exc)
        owner._compact_error_text = lambda text,*args:text
        def send(page,request,**kwargs):
            index = int(request)
            attempts[index] = attempts.get(index,0)+1
            state['index'] = index
            state['failure'] = index == fail_index and (always_fail_second or attempts[index] == 1)
            state['pending'] = state['failure'] and not acknowledged_timeout
            if not state['pending']:
                state['ack'] += 1
                state['ack_delay'] = 4 if delayed_ack else 0
        def wait(*args,**kwargs):
            if state.get('failure'):
                raise RuntimeError('ChatGPT 이미지 생성 결과를 제한 시간 안에 찾지 못했습니다.')
            return {'index':state['index']}
        owner._send_prompt_to_gpt_page = send
        owner._wait_for_chatgpt_generated_image = wait
        owner._save_chatgpt_generated_image = lambda page,candidate,path:path.write_bytes(b'test-image')
        with tempfile.TemporaryDirectory(prefix='thumbnail-flow-') as tmp:
            product = types.SimpleNamespace(index=0,output_dir=Path(tmp))
            log = product.output_dir/'thumbnail_prompts/thumbnail_02_retry.log'
            log.parent.mkdir()
            log.write_text('previous failure\n',encoding='utf-8')
            if existing_first:
                first = product.output_dir/'thumbnails/1.png'
                first.parent.mkdir()
                first.write_bytes(b'previous-valid-image')
            def tick(ms):
                state['ack_delay'] = max(0,state.get('ack_delay',0)-1)
            page = types.SimpleNamespace(
                evaluate=lambda script:'turn-'+str(state['ack']-(1 if state.get('ack_delay',0) else 0)),
                wait_for_timeout=tick)
            result = types.FunctionType(code,env)(owner,product,[],'TEST',page=page,resume_from_thumbnail=None,progress_callback=None)
            self.assertTrue(log.read_text(encoding='utf-8').startswith('previous failure\n'))
            if existing_first:
                self.assertEqual(first.read_bytes(),b'previous-valid-image')
            return [int(p.stem) for p in result.paths],attempts

    def test_unsent_second_thumbnail_retries_without_restarting_first(self):
        indices,attempts = self.run_flow()
        self.assertEqual(indices,[1,2,3,4,5])
        self.assertEqual(attempts,{1:1,2:2,3:1,4:1,5:1})

    def test_three_failures_continue_to_remaining_thumbnails_without_false_success(self):
        indices,attempts = self.run_flow(always_fail_second=True)
        self.assertEqual(indices,[1,3,4,5])
        self.assertEqual(attempts,{1:1,2:3,3:1,4:1,5:1})

    def test_acknowledged_image_timeouts_retry_each_of_five_indices(self):
        for index in range(1,6):
            with self.subTest(index=index):
                indices,attempts = self.run_flow(fail_index=index,acknowledged_timeout=True)
                self.assertEqual(indices,[1,2,3,4,5])
                self.assertEqual(attempts[index],2)

    def test_three_timeouts_apply_to_every_index_and_keep_later_work(self):
        for index in range(1,6):
            with self.subTest(index=index):
                indices,attempts = self.run_flow(always_fail_second=True,fail_index=index,acknowledged_timeout=True)
                self.assertEqual(indices,[n for n in range(1,6) if n != index])
                self.assertEqual(attempts[index],3)
                self.assertEqual(set(attempts),set(range(1,6)))

    def test_resume_keeps_existing_first_thumbnail(self):
        indices,attempts = self.run_flow(existing_first=True)
        self.assertEqual(indices,[1,2,3,4,5])
        self.assertNotIn(1,attempts)

    def test_virtualized_message_count_and_delayed_ack_do_not_duplicate_requests(self):
        indices,attempts = self.run_flow(fail_index=0,delayed_ack=True)
        self.assertEqual(indices,[1,2,3,4,5])
        self.assertEqual(attempts,{index:1 for index in range(1,6)})


if __name__ == '__main__':
    unittest.main(verbosity=2)
