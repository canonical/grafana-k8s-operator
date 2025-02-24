#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import logging

from charms.grafana_k8s.v0.grafana_metadata import GrafanaMetadataRequirer as Requirer
from ops import ActionEvent, CollectStatusEvent, WaitingStatus
from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus

logger = logging.getLogger(__name__)


class MetadataTester(CharmBase):
    def __init__(self, framework):
        super().__init__(framework)
        self.metadata_relation = Requirer(self.model.relations, "metadata")

        self.framework.observe(self.on.collect_unit_status, self.on_collect_unit_status)
        self.framework.observe(self.on.get_metadata_action, self.on_get_metadata)

    def on_collect_unit_status(self, event: CollectStatusEvent):
        statuses = []
        if len(self.metadata_relation.relations) == 0:
            statuses.append(WaitingStatus("Waiting for metadata relation"))
        else:
            relation_data = self.metadata_relation.get_data()
            if relation_data is None:
                statuses.append(WaitingStatus("Metadata relation found but no data available yet"))
            else:
                statuses.append(
                    ActiveStatus(
                        f"Alive with metadata relation data: '{relation_data.model_dump(mode='json')}'"
                    )
                )
        for status in statuses:
            event.add_status(status)

    def on_get_metadata(self, event: ActionEvent):
        relation_data = self.metadata_relation.get_data()
        if relation_data is None:
            relation_data = {}
        else:
            relation_data = relation_data.model_dump(mode='json')
        event.set_results({"relation-data": json.dumps(relation_data)})


if __name__ == "__main__":
    main(MetadataTester)
