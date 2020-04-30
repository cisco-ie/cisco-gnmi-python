"""Copyright 2019 Cisco Systems
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

 * Redistributions of source code must retain the above copyright
 notice, this list of conditions and the following disclaimer.

The contents of this file are licensed under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""

"""Contains useful functionality generally applicable for manipulation of cisco_gnmi."""

import logging
import ssl

from cryptography import x509
from cryptography.hazmat.backends import default_backend

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse


LOGGER = logging.getLogger(__name__)
logger = LOGGER


def gen_target_netloc(target, netloc_prefix="//", default_port=9339):
    """Parses and validates a supplied target URL for gRPC calls.
    Uses urllib to parse the netloc property from the URL.
    netloc property is, effectively, fqdn/hostname:port.
    This provides some level of URL validation and flexibility.
    9339 is IANA reserved port for gNMI/gNOI/...
    Returns netloc property of target.
    """
    if netloc_prefix not in target:
        target = netloc_prefix + target
    parsed_target = urlparse(target)
    if not parsed_target.netloc:
        raise ValueError("Unable to parse netloc from target URL %s!" % target)
    if parsed_target.scheme:
        LOGGER.debug("Scheme identified in target, ignoring and using netloc.")
    target_netloc = parsed_target
    if parsed_target.port is None:
        ported_target = "%s:%i" % (parsed_target.hostname, default_port)
        LOGGER.debug("No target port detected, reassembled to %s.", ported_target)
        target_netloc = gen_target_netloc(ported_target)
    return target_netloc


def validate_proto_enum(
    value_name, value, enum_name, enum, subset=None, return_name=False
):
    """Helper function to validate an enum against the proto enum wrapper."""
    enum_value = None
    if value not in enum.keys() and value not in enum.values():
        raise Exception(
            "{name}={value} not in {enum_name} enum! Please try any of {options}.".format(
                name=value_name,
                value=str(value),
                enum_name=enum_name,
                options=str(enum.keys()),
            )
        )
    if value in enum.keys():
        enum_value = enum.Value(value)
    else:
        enum_value = value
    if subset:
        resolved_subset = []
        for element in subset:
            if element in enum.keys():
                resolved_subset.append(enum.Value(element))
            elif element in enum.values():
                resolved_subset.append(element)
            else:
                raise Exception(
                    "Subset element {element} not in {enum_name}!".format(
                        element=element, enum_name=enum_name
                    )
                )
        if enum_value not in resolved_subset:
            raise Exception(
                "{name}={value} ({actual_value}) not in subset {subset} ({actual_subset})!".format(
                    name=value_name,
                    value=value,
                    actual_value=enum_value,
                    subset=subset,
                    actual_subset=resolved_subset,
                )
            )
    return enum_value if not return_name else enum.Name(enum_value)


def get_cert_from_target(target_netloc):
    """Retrieves the SSL certificate from a secure server."""
    return ssl.get_server_certificate(
        (target_netloc.hostname, target_netloc.port)
    ).encode("utf-8")


def get_cn_from_cert(cert_pem):
    """Attempts to derive the CN from a supplied certficate.
    Defaults to first found if multiple CNs identified.
    """
    cert_cn = None
    cert_parsed = x509.load_pem_x509_certificate(cert_pem, default_backend())
    cert_cns = cert_parsed.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
    if len(cert_cns) > 0:
        if len(cert_cns) > 1:
            LOGGER.warning(
                "Multiple CNs found for certificate, defaulting to the first one."
            )
        cert_cn = cert_cns[0].value
        LOGGER.debug("Using %s as certificate CN.", cert_cn)
    else:
        LOGGER.warning("No CN found for certificate.")
    return cert_cn
