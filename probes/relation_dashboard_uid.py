import base64
import json
import lzma
import re


def show_unit(juju_show_units):
    for show_unit in juju_show_units.values():
        if show_unit is None:
            continue
        unit_name = next(iter(show_unit))
        # 1. Extract the relation-info
        relation_info = show_unit[unit_name]["relation-info"]
        # 2. Extract the "grafana" endpoint relations
        grafana_endpoints = [
            relation for relation in relation_info if relation["endpoint"] == "grafana"
        ]

        assert len(grafana_endpoints) > 0

        for grafana_endpoint in grafana_endpoints:
            # 3. Extract the application data
            app_data = grafana_endpoint["application-data"]
            relation_id = grafana_endpoint["relation-id"]
            # 4. Convert dashboard data to JSON and decode
            dashboards = json.loads(app_data["dashboards"])
            for id in dashboards:
                for meta in dashboards[id]:
                    decoded_uid = _uid_from_encoded_dashboard(meta["content"])
                    # 5. Check if the top-level UID exist and is not empty
                    if not _is_valid_format(decoded_uid):
                        raise Exception(
                            f"Invalid dashboard UID ({id}) for relation-id ({relation_id})"
                        )


def _uid_from_encoded_dashboard(data: bytes) -> str:
    decoded_data = base64.b64decode(data)
    decompressed_data = lzma.decompress(decoded_data)
    return json.loads(decompressed_data).get("uid")


def _is_valid_format(uid: str) -> bool:
    if not uid:
        return False
    # https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/#identifier-id-vs-unique-identifier-uid
    if len(uid) > 40:
        return False
    # https://community.grafana.com/t/which-characters-will-never-appear-in-a-dashboard-uid/11500
    for char in uid:
        if not re.match(r"[a-zA-Z0-9_-]", char):
            return False

    return True
