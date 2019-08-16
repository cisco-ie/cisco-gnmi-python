"""Copyright 2019 Cisco Systems All rights reserved.

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

"""Python gNMI wrapper to ease usage."""

import logging
import json

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

import grpc
from . import proto


class Client(object):
    """This class creates grpc calls using python.
    """

    """Defining property due to gRPC timeout being based on a C long type.
    Should really define this based on architecture.
    32-bit C long max value. "Infinity".
    """
    __C_MAX_LONG = 2147483647

    def __init__(
        self,
        target,
        username,
        password,
        timeout=__C_MAX_LONG,
        credentials=None,
        credentials_from_file=False,
        tls_server_override=None,
        tls_enabled=True,
    ):
        self.username = username
        self.password = password
        self.timeout = int(timeout)
        self.tls_enabled = tls_enabled
        self.__target = self.__gen_target(target)
        self.__credentials = self.__gen_credentials(credentials, credentials_from_file)
        self.__options = self.__gen_options(tls_server_override)
        self.__client = self.__gen_client(
            self.__target, self.__credentials, self.__options, self.tls_enabled
        )

    def __repr__(self):
        """JSON dump a dict of basic attributes."""
        return json.dumps(
            {
                "target": self.__target,
                "tls_enabled": self.tls_enabled,
                "is_secure": bool(self.__credentials),
                "username": self.username,
                "password": self.password,
                "timeout": self.timeout,
            }
        )

    def __gen_metadata(self):
        """Generates expected gRPC call metadata."""
        return [("username", self.username), ("password", self.password)]

    def capabilities(self):
        """Capabilities allows the client to retrieve the set of capabilities that
        is supported by the target. This allows the target to validate the
        service version that is implemented and retrieve the set of models that
        the target supports. The models can then be specified in subsequent RPCs
        to restrict the set of data that is utilized.
        Reference: gNMI Specification Section 3.2
        """
        message = proto.gnmi_pb2.CapabilityRequest()
        response = self.__client.Capabilities(message, metadata=self.__gen_metadata())
        return response

    def get(
        self,
        path,
        prefix=None,
        data_type=proto.gnmi_pb2.GetRequest.DataType.ALL,
        encoding=proto.gnmi_pb2.Encoding.JSON_IETF,
        use_models=None,
        extension=None,
    ):
        """
        A snapshot of the state that exists on the target
        :param path: A set of paths to request data snapshot
        :param prefix: a path that is applied to all paths
        :param data_type: type of data requested [CONFIG, STATE, OPERATIONAL]
        :param encoding: Data format data comes out in 2=Proto, 0=JSON
        :param use_models: ModelData messages indicating the schema definition
        :param extension: a repeated field to carry gNMI extensions
        :type path:
        :type prefix:
        :type gnmi_type: string
        :type encoding: int
        :type use_models:
        :type extension:
        :return: Return the response object
        :rtype:
        """
        data_type = self.__check_proto_enum(
            "data_type",
            data_type,
            "GetRequest.DataType",
            proto.gnmi_pb2.GetRequest.DataType,
        )
        encoding = self.__check_proto_enum(
            "encoding", encoding, "Encoding", proto.gnmi_pb2.Encoding
        )
        request = proto.gnmi_pb2.GetRequest()
        if not isinstance(path, (list, set)):
            request.path.append(path)
        else:
            for single_path in path:
                request.path.append(single_path)
        request.type = data_type
        request.encoding = encoding
        if prefix:
            request.prefix = prefix
        if use_models:
            request.use_models = use_models
        if extension:
            request.extension = extension
        response = self.__client.Get(request, metadata=self.__gen_metadata())
        return response

    def get_xpaths(
        self,
        xpaths,
        data_type='ALL',
        encoding='JSON_IETF',
    ):
        gnmi_path = None
        if isinstance(xpaths, (list, set)):
            gnmi_path = map(self.__parse_xpath_to_gnmi_path, set(xpaths))
        elif isinstance(xpaths, str):
            gnmi_path = [self.__parse_xpath_to_gnmi_path(xpaths)]
        else:
            raise Exception(
                "xpaths must be a single xpath string or iterable of xpath strings!"
            )
        return self.get(gnmi_path, data_type=data_type, encoding=encoding)

    def set(self, prefix=None, update=None, replace=None, delete=None, extension=None):
        """
        Modifications to the state of the target are made through the Set RPC.
        A client sends a SetRequest message to the target indicating the modifications
        it desires.
        :param prefix: The prefix specified is applied to all paths defined within other fields of the message.
        :param update: A set of messages indicating elements of the data tree whose content is to be updated
        :param replace: A set of messages indicating elements of the data tree whose contents is to be replaced
        :param delete: A set of paths which are to be removed from the data tree.
        :param extension: Repeated field used to carry gNMI extensions
        :type prefix:
        :type update:
        :type replace:
        :type delete:
        :return: SetResonse with the following fields: prefix, response, extension
        """
        request = proto.gnmi_pb2.SetRequest(
            prefix=prefix, update=update, replace=replace, delete=delete
        )
        response = self.__client.Set(request, metadata=self.__gen_metadata())
        return response

    @staticmethod
    def __gen_target(target, netloc_prefix="//", default_port=50051):
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
            target_netloc = Client.__gen_target(ported_target)
        return target_netloc

    @staticmethod
    def __gen_client(target, credentials=None, options=None, tls_enabled=True):
        """Instantiates and returns the NX-OS gRPC client stub
        over an insecure or secure channel.
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

    @staticmethod
    def __gen_credentials(credentials, credentials_from_file):
        """Generate credentials either by reading credentials from
        the specified file or return the original creds specified.
        """
        if not credentials:
            return None
        if credentials_from_file:
            with open(credentials, "rb") as creds_fd:
                credentials = creds_fd.read()
        return credentials

    @staticmethod
    def __gen_options(tls_server_override):
        """Generate options tuple for gRPC overrides, etc.
        Only TLS server is handled currently.
        """
        options = []
        if tls_server_override:
            options.append(("grpc.ssl_target_name_override", tls_server_override))
        return tuple(options)

    @staticmethod
    def __parse_xpath_to_gnmi_path(xpath):
        if not isinstance(xpath, str):
            raise Exception("xpath must be a string!")
        path = proto.gnmi_pb2.Path()
        for element in xpath.split("/"):
            path.elem.append(proto.gnmi_pb2.PathElem(name=element))
        return path

    @staticmethod
    def __validate_enum_arg(name, valid_options, message=None):
        """Construct error around enumeration validation."""
        if name not in valid_options:
            if not message:
                message = "%s must be one of %s" % (name, ", ".join(valid_options))
            raise ValueError(message)

    @staticmethod
    def __check_proto_enum(value_name, value, enum_name, enum):
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
