import unittest

from parental_control import get_effective_restrictions


class LockdownRulesTests(unittest.TestCase):
    def test_no_session_uses_default_lockdown_lists(self):
        programs, sites = get_effective_restrictions(
            "trave",
            session=None,
            default_programs=["chrome.exe"],
            default_websites=["youtube.com"],
        )

        self.assertEqual(programs, ["chrome.exe"])
        self.assertEqual(sites, ["youtube.com"])

    def test_active_session_keeps_session_specific_lists(self):
        session = {
            "blocked_programs": ["minecraft.exe"],
            "blocked_websites": ["tiktok.com"],
        }
        programs, sites = get_effective_restrictions(
            "trave",
            session=session,
            default_programs=["chrome.exe"],
            default_websites=["youtube.com"],
        )

        self.assertEqual(programs, ["minecraft.exe"])
        self.assertEqual(sites, ["tiktok.com"])


if __name__ == "__main__":
    unittest.main()
