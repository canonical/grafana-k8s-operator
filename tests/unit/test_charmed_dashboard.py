import unittest
from pathlib import Path

from charms.grafana_k8s.v0.grafana_dashboard import CharmedDashboard

UNIT_TEST_DIR = Path(__file__).parent


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

def test_load_dashboards_from_dir():
    # GIVEN a dashboards directory with three subfolders each containing one dashboard
    dashboards_path = UNIT_TEST_DIR / "nested_dashboard_templates"

    # WHEN load_dashboards_from_dir is called
    result = CharmedDashboard.load_dashboards_from_dir(
        dashboards_path=dashboards_path,
        charm_name="my-charm",
        charm_dir=UNIT_TEST_DIR,
        inject_dropdowns=False,
        juju_topology={},
    )

    # THEN all three dashboards are returned (one per subfolder)
    assert len(result) == 3
    assert "file:dashboard_a" in result
    assert "file:dashboard_b" in result
    assert "file:dashboard_c" in result

if __name__ == '__main__':
    unittest.main()
