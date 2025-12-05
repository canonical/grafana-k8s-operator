# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

import json
from typing import List, Dict

class FakeProcessVersionCheck:
    def __init__(self, args):
        pass

    def wait_output(self):
        return ("Version 0.1.0", "")

    def wait(self):
        return


def conv_dashboard_list(dashboards: List[Dict]) -> str:
    # For diff purposes, replace contents (str) with parsed dashboard (dict)
    # so that order of keys won't fail the str comparison.
    # Then dump to pretty string so diff is easier to sift through
    return json.dumps([{**d, **{"content": json.loads(d["content"])}} for d in dashboards], sort_keys=True, indent=2)
