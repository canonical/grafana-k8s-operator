# GIVEN reldata with two dashboard "objects" with distinct 'uid' and 'version'
# WHEN the charm provision the dashboards (writes the to disk)
# THEN both dashboards are on disk


# GIVEN reldata with two dashboard "objects" with distinct 'uid' but same 'version'
# WHEN the charm provision the dashboards (writes the to disk)
# THEN both dashboards are on disk


# GIVEN reldata with two dashboard "objects" with the same 'uid' but different 'version'
# WHEN the charm provision the dashboards (writes the to disk)
# THEN only one dashboard is written to disk - the dashboard with the higher version


# GIVEN reldata with two dashboard "objects" with the same 'uid' and same 'version'
# WHEN the charm provision the dashboards (writes the to disk)
# THEN only one dashboard is written to disk - the dashboard with the TODO: sorted hash?


