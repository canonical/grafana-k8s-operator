# These are the required and optional relation data fields
# In other words, when relating to this charm, these are the fields
# that will be processed by this charm.
REQUIRED_DATASOURCE_FIELDS = {
    'private-address',  # the hostname/IP of the data source server
    'port',  # the port of the data source server
    'source-type',  # the data source type (e.g. prometheus)
}

OPTIONAL_DATASOURCE_FIELDS = {
    'source-name',  # a human-readable name of the source
}

# https://grafana.com/docs/grafana/latest/administration/configuration/#database
REQUIRED_DATABASE_FIELDS = {
    'type',  # mysql, postgres or sqlite3 (sqlite3 doesn't work for HA)
    'host',  # in the form '<url_or_ip>:<port>', e.g. 127.0.0.1:3306
    'name',
    'user',
    'password',
}

# verify with Grafana documentation to ensure fields have valid values
# as this charm will not directly handle these cases
# TODO: fill with optional fields
OPTIONAL_DATABASE_FIELDS = set()

VALID_DATABASE_TYPES = {'mysql', 'postgres', 'sqlite3'}