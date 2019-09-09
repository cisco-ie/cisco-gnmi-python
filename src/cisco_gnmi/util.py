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

import logging

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

from six import string_types
import grpc
from . import proto


def gen_target(target, netloc_prefix="//", default_port=50051):
    """Parses and validates a supplied target URL for gRPC calls.
    Uses urllib to parse the netloc property from the URL.
    netloc property is, effectively, fqdn/hostname:port.
    This provides some level of URL validation and flexibility.
    Returns netloc property of target.
    """
    if netloc_prefix not in target:
        target = netloc_prefix + target
    parsed_target = urlparse(target)
    if not parsed_target.netloc:
        raise ValueError("Unable to parse netloc from target URL %s!" % target)
    if parsed_target.scheme:
        logging.debug("Scheme identified in target, ignoring and using netloc.")
    target_netloc = parsed_target.netloc
    if parsed_target.port is None:
        ported_target = "%s:%i" % (parsed_target.hostname, default_port)
        logging.debug("No target port detected, reassembled to %s.", ported_target)
        target_netloc = gen_target(ported_target)
    return target_netloc


def gen_client(target, credentials=None, options=None, tls_enabled=True):
    """Instantiates and returns the gNMI gRPC client stub over
    an insecure or secure channel.
    """
    client = None
    if not tls_enabled:
        logging.warning(
            "TLS MUST be enabled per gNMI specification. If your gNMI implementation works without TLS, it is non-compliant."
        )
        insecure_channel = grpc.insecure_channel(target)
        client = proto.gnmi_pb2_grpc.gNMIStub(insecure_channel)
    else:
        channel_creds = grpc.ssl_channel_credentials(credentials)
        secure_channel = grpc.secure_channel(target, channel_creds, options)
        client = proto.gnmi_pb2_grpc.gNMIStub(secure_channel)
    return client


def gen_credentials(credentials, credentials_from_file):
    """Generate credentials either by reading credentials from
    the specified file or return the original creds specified.
    """
    if not credentials:
        return None
    if credentials_from_file:
        with open(credentials, "rb") as creds_fd:
            credentials = creds_fd.read()
    return credentials


def gen_options(tls_server_override):
    """Generate options tuple for gRPC overrides, etc.
    Only TLS server is handled currently.
    """
    options = []
    if tls_server_override:
        options.append(("grpc.ssl_target_name_override", tls_server_override))
    return tuple(options)


def parse_xpath_to_gnmi_path(xpath, origin=None):
    """Parses an XPath to proto.gnmi_pb2.Path."""
    if not isinstance(xpath, string_types):
        raise Exception("xpath must be a string!")
    path = proto.gnmi_pb2.Path()
    if origin:
        if not isinstance(origin, string_types):
            raise Exception("origin must be a string!")
        path.origin = origin
    for element in xpath.split("/"):
        path.elem.append(proto.gnmi_pb2.PathElem(name=element))
    return path


def validate_proto_enum(value_name, value, enum_name, enum):
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
    return enum_value
