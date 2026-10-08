import os
import unittest
from unittest.mock import Mock, patch

import requests
import checkin

COOKIE = 'gld:sess=value; gld:sess.sig=signature'


def response(data):
    return Mock(status_code=200, json=Mock(return_value=data))


class CheckinTests(unittest.TestCase):
    def run_accounts(self, messages, cookies=COOKIE):
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.post.side_effect = [response(m) for m in messages]
        session.get.return_value = response({'data': {}})
        with patch.dict(os.environ, {'COOKIES': cookies}, clear=True), \
                patch.object(checkin.requests, 'Session', return_value=session), \
                patch.object(checkin, 'get_candidate_domains', return_value=['glados.cloud']), \
                patch.object(checkin, 'push_all', return_value=(1, 1)) as push, \
                patch.object(checkin.time, 'sleep'):
            code = checkin.main()
        return code, push, session

    def test_permission_denied(self):
        code, push, _ = self.run_accounts([{'code': 1, 'message': '没有权限'}])
        self.assertEqual(code, 1)
        self.assertIn('重新获取 Cookie', push.call_args.args[1])

    def test_success_repeat_and_mixed_failure(self):
        for code in (0, 1):
            self.assertEqual(self.run_accounts([{'code': code, 'message': 'ok'}])[0], 0)
        self.assertEqual(self.run_accounts(
            [{'message': '没有权限'}, {'code': 0}], COOKIE + ' & ' + COOKIE)[0], 1)

    def test_missing_or_invalid_cookie(self):
        for cookie in ('', 'gld:sess=only'):
            code, _, session = self.run_accounts([], cookie)
            self.assertEqual(code, 1)
            session.post.assert_not_called()

    def test_cookie_normalization_and_prefixes(self):
        for prefix in ('koa', 'gld', 'future'):
            cookie = f'{prefix}:sess=value; {prefix}:sess.sig=sig'
            self.assertTrue(checkin.validate_cookie(cookie)[0])
            self.assertEqual(checkin.normalize_cookie('"Cookie: ' + cookie + '"'), cookie)
        self.assertFalse(checkin.validate_cookie('gld:sess=a; koa:sess.sig=b')[0])

    def test_multiple_cookie_separators(self):
        for sep in (' & ', '\n', '|||'):
            code, _, session = self.run_accounts([{'code': 0}, {'code': 1}], COOKIE + sep + COOKIE)
            self.assertEqual(code, 0)
            self.assertEqual(session.post.call_count, 2)
            self.assertEqual(session.cookies.clear.call_count, 2)

    def test_domain_fallback_and_token(self):
        session = Mock()
        session.post.side_effect = [response({'message': '没有权限'}), response({'code': 0})]
        session.get.return_value = response({'data': {}})
        with patch.dict(os.environ, {'GLADOS_SITE': 'https://glados.one/console'}, clear=True):
            acc = checkin.checkin_account(session, COOKIE, 1)
        self.assertEqual(acc['domain'], 'glados.cloud')
        self.assertEqual(session.post.call_args_list[0].args[0], 'https://glados.one/api/user/checkin')
        self.assertEqual(session.post.call_args.kwargs['json'], {'token': 'glados.cloud'})
        self.assertEqual(session.post.call_count, 2)

    def test_points_detail_and_legacy_success(self):
        code, push, _ = self.run_accounts([{'code': 1, 'message': 'Observation logged', 'list': [
            {'asset': 'points', 'balance': '12.50', 'change': '1.5'}]}])
        self.assertEqual(code, 0)
        self.assertIn('总积分:12.5', push.call_args.args[1])
        self.assertIn('奖励:1.5 积分', push.call_args.args[1])
        self.assertIn('✅1', push.call_args.args[0])

    def test_telegram_aliases(self):
        for env in ({'TELEGRAM_BOT_TOKEN': 'old', 'TELEGRAM_CHAT_ID': 'chat',
                     'TG_BOT_TOKEN': 'new', 'TG_CHAT_ID': 'newchat'},
                    {'TG_BOT_TOKEN': 'old', 'TG_CHAT_ID': 'chat'}):
            with patch.dict(os.environ, env, clear=True), patch.object(checkin, 'push_telegram', return_value=True) as push:
                self.assertEqual(checkin.push_all('title', 'content'), (1, 1))
                push.assert_called_once_with('old', 'chat', 'title', 'content')

    def test_telegram_preserves_long_content(self):
        content = '长消息😀' * 3000
        with patch.object(checkin, '_push_request', return_value=True) as push:
            self.assertTrue(checkin.push_telegram('token', 'chat', 'title', content))
        chunks = [call.kwargs['json_payload']['text'] for call in push.call_args_list]
        self.assertEqual(''.join(chunks), 'title\n\n' + content)
        self.assertTrue(all(len(c.encode('utf-16-le')) // 2 <= 4096 for c in chunks))

    def test_retry_and_exchange_no_retry(self):
        session = Mock()
        session.post.side_effect = [requests.exceptions.Timeout(), response({'code': 0})]
        with patch.object(checkin.time, 'sleep'):
            self.assertEqual(checkin.checkin_request(session, {'origin': 'https://glados.cloud'}), {'code': 0})
        self.assertEqual(session.post.call_count, 2)
        session.reset_mock()
        session.post.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(requests.exceptions.Timeout):
            checkin.exchange_request(session, {'origin': 'https://glados.cloud'}, 'plan100')
        self.assertEqual(session.post.call_count, 1)

    def test_exchange_disabled_by_default(self):
        _, _, session = self.run_accounts([{'code': 0}])
        self.assertEqual(session.post.call_count, 1)


if __name__ == '__main__':
    unittest.main()
