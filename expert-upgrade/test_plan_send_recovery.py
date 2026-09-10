import marshal
import types
import unittest
from unittest.mock import Mock
import build_upgrade as b

class PlanSendRecoveryTests(unittest.TestCase):
    def run_submit(self,accepted,delayed=0):
        entry=next(e for e in b.read_archive(b.TARGET).entries if e.name=='detail_page_automation_gui')
        code=b.find(marshal.loads(b.entry_payload(entry)),'_submit_section_plan_request')
        owner=types.SimpleNamespace()
        for name in ('_ensure_chatgpt_section_planner_page','_accept_chatgpt_cookies','_wait_for_gpt_idle','_raise_if_user_requested_stop_or_skip'):
            setattr(owner,name,Mock())
        owner._page_needs_login=lambda page:False
        owner._latest_gpt_text=lambda page:('old response',False)
        owner._find_reusable_gpt_plan_on_page=lambda *args:''
        owner._can_reuse_existing_gpt_plan=lambda *args:False
        owner._should_retry_chatgpt_image_request=lambda exc:'프롬프트가 입력창' in str(exc)
        owner._wait_for_gpt_section_plan_detection=Mock(return_value='NEW COMPLETE PLAN')
        state={'sent':False,'ticks':0}
        def send(*args,**kwargs):
            state['sent']=True
            raise RuntimeError('ChatGPT 전송 후에도 프롬프트가 입력창에 남아 있습니다.')
        owner._send_prompt_to_gpt_page=Mock(side_effect=send)
        def tick(ms):state['ticks']+=1
        page=types.SimpleNamespace(evaluate=lambda script:['turn-1','turn-3'] if accepted and state['sent'] and state['ticks']>=delayed else ['turn-1'],wait_for_timeout=tick)
        result=types.FunctionType(code,{'CHATGPT_SECTION_PLAN_WAIT_TIMEOUT_SECONDS':210})(owner,page,'PROMPT',attachment_paths=[],allow_retry=True,product=None)
        self.assertEqual(owner._send_prompt_to_gpt_page.call_count,1)
        self.assertEqual(owner._wait_for_gpt_section_plan_detection.call_count,1)
        return result
    def test_accepted_request_with_send_ui_error_waits_for_plan(self):
        self.assertEqual(self.run_submit(True),'NEW COMPLETE PLAN')
    def test_delayed_new_user_turn_does_not_trigger_duplicate_send(self):
        self.assertEqual(self.run_submit(True,delayed=4),'NEW COMPLETE PLAN')
    def test_unaccepted_request_stays_failed(self):
        with self.assertRaisesRegex(RuntimeError,'프롬프트가 입력창'):
            self.run_submit(False)

if __name__=='__main__':unittest.main(verbosity=2)
