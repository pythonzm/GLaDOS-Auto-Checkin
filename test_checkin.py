import unittest
from unittest.mock import Mock, patch

import checkin


class CheckinExitTests(unittest.TestCase):
    def run_accounts(self, messages, cookies="dummy"):
        session = Mock()
        session.post.side_effect = [
            Mock(status_code=200, json=Mock(return_value={"message": message}))
            for message in messages
        ]
        session.get.return_value.json.return_value = {"data": {}}
        with patch.dict("os.environ", {"COOKIES": cookies}, clear=True), \
                patch.object(checkin.requests, "Session", return_value=session), \
                patch.object(checkin, "get_candidate_domains", return_value=["glados.one"]), \
                patch.object(checkin, "console_print") as output, \
                patch.object(checkin, "push_telegram") as push, \
                patch.object(checkin.time, "sleep"):
            code = checkin.main()
        return code, output, push

    def test_permission_denied_fails_after_notification(self):
        code, output, push = self.run_accounts(["没有权限"])
        self.assertEqual(code, 1)
        self.assertIn("登录校验失败", output.call_args_list[0].args[0])
        self.assertIn("没有权限", push.call_args.args[3])

    def test_success_and_repeat_succeed(self):
        for message in ("checkin! get 1 day", "already checked in"):
            with self.subTest(message=message):
                self.assertEqual(self.run_accounts([message])[0], 0)

    def test_one_failed_account_fails_whole_run(self):
        code, _, push = self.run_accounts(
            ["没有权限", "already checked in"], "first & second"
        )
        self.assertEqual(code, 1)
        self.assertIn("❌1 🔁1", push.call_args.args[2])

    def test_missing_cookies_fails(self):
        self.assertEqual(self.run_accounts([], cookies="")[0], 1)

    def test_unusable_response_fails(self):
        self.assertEqual(self.run_accounts([""])[0], 1)


if __name__ == "__main__":
    unittest.main()
