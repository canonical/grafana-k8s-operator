import unittest
from charms.grafana_k8s.v0.grafana_dashboard import CharmedDashboard


class CharmedDashboardTest(unittest.TestCase):
    def test_add_tags_to_dashboard_without_tags(self):
        # GIVEN a dashboard dict with no tags
        dashboard = {}

        # WHEN tags are added
        CharmedDashboard._add_tags(dashboard, "my-charm")

        # THEN list of tags only contains MyCharm
        self.assertListEqual(dashboard["tags"], ["charm: my-charm"])

    def test_add_tags_to_dashboard_with_tags(self):
        # GIVEN a dashboard dict with some tags
        dashboard = {"tags": ["one", "two"]}

        # WHEN tags are added
        CharmedDashboard._add_tags(dashboard, "my-charm")

        # THEN list of tags is extended with MyCharm
        self.assertListEqual(dashboard["tags"], ["one", "two", "charm: my-charm"])

    def test_add_tags_to_dashboard_with_charm_tag(self):
        # GIVEN a dashboard dict with a tag that starts with "charm: "
        dashboard = {"tags": ["charm: something-else"]}

        # WHEN tags are added
        CharmedDashboard._add_tags(dashboard, "my-charm")

        # THEN list of tags is unaffected
        self.assertListEqual(dashboard["tags"], ["charm: something-else"])


if __name__ == "__main__":
    unittest.main()
