from interface_tester import InterfaceTester


def test_grafana_datasource_v0_interface(grafana_source_tester: InterfaceTester):
    grafana_source_tester.configure(
        interface_name="grafana_datasource",
        interface_version=0,
    )
    grafana_source_tester.run()
