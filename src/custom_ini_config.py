# Copyright 2026 Canonical
# See LICENSE file for licensing details.

"""Validation for custom ("extra") ini sections."""

from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, ValidationError, ConfigDict
import configparser

class _SMTPSection(BaseModel):
    """SMTP server settings.

    Ref: https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/#smtp
    """

    model_config = ConfigDict(extra='forbid')

    enabled: Optional[bool] = None
    """Enable this to allow Grafana to send email."""

    host: Optional[str] = None
    """Default is localhost:25. Use port 465 for implicit TLS."""

    user: Optional[str] = None
    """In case of SMTP auth, default is empty."""

    password: Optional[str] = None
    """In case of SMTP auth, default is empty. If the password contains # or ;, then you have to wrap it with triple quotes. Example: \"\"\"#password;\"\"\""""

    cert_file: Optional[str] = None
    """File path to a cert file, default is empty."""

    key_file: Optional[str] = None
    """File path to a key file, default is empty."""

    skip_verify: bool = False
    """Verify SSL for SMTP server, default is false."""

    from_address: Optional[EmailStr] = None
    """Address used when sending out emails, default is admin@grafana.localhost."""

    from_name: Optional[str] = None
    """Name to be used when sending out emails, default is Grafana."""

    ehlo_identity: Optional[str] = None
    """Name to be used as client identity for EHLO in SMTP conversation, default is <instance_name>."""

    startTLS_policy: Optional[Literal["OpportunisticStartTLS", "MandatoryStartTLS", "NoStartTLS"]] = None  # noqa: N815
    """Either OpportunisticStartTLS, MandatoryStartTLS, NoStartTLS, or empty. Default is empty."""

    enable_tracing: Optional[bool] = None
    """Enable trace propagation in email headers, using the traceparent, tracestate and (optionally) baggage fields. Default is false. To enable, you must first configure tracing in one of the tracing.opentelemetry.* sections."""


def validate(ini_sections: Optional[str]=None):
    """Validate custom ini sections.

    Raises:
        ValueError: If ini_sections is not valid.
    """
    if ini_sections is None:
        return

    config = configparser.ConfigParser()

    try:
        config.read_string(ini_sections)
    except configparser.Error as e:
        raise ValueError(f"Invalid ini sections. Parsing error: {e}") from e

    # Only select sections are permitted
    sections = {"smtp": _SMTPSection}
    permitted_sections = set(sections.keys())
    actual_sections = set(config.sections())
    if not permitted_sections >= actual_sections:
        raise ValueError(f"Invalid ini sections. Permitted sections: {permitted_sections}; unallowed sections: {actual_sections - permitted_sections}.")

    for name, validator in sections.items():
        if config.has_section(name):
            try:
                validator.model_validate(config[name])
            except ValidationError as e:
                raise ValueError(f"Invalid [{name}] section: {e}")

