import unittest

from cloudrise.demo import demo_dashboard


class DemoTests(unittest.TestCase):
    def test_demo_is_explicitly_labeled_and_not_transmitted(self) -> None:
        dashboard = demo_dashboard()
        self.assertEqual("demo", dashboard["mode"])
        self.assertIn("DEMO REPLAY", dashboard["mode_label"])
        self.assertIn("never transmits", dashboard["last_action"]["detail"])
        self.assertEqual(100000, dashboard["account"]["starting_equity"])


if __name__ == "__main__":
    unittest.main()

