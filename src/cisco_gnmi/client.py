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

"""Python gNMI wrapper to ease usage of gNMI."""

import json

from . import proto
from . import util


class Client(object):
    """gNMI gRPC wrapper client to ease usage of gNMI.

    Returns relatively raw response data. Response data may be accessed according
    to the gNMI specification.

    Attributes
    ----------
    username : str
    password : str
    timeout : uint
    tls_enabled : bool

    Methods
    -------
    capabilities()
        Retrieve meta information about version, supported models, etc.
    get(...)
        Get a snapshot of config, state, operational, or all forms of data.
    set(...)
        Update, replace, or delete configuration.
    subscribe(...)
        Stream snapshots of data from the device.

    Examples
    --------
    >>> from gnmi import Client
    >>> client = Client('127.0.0.1:57400', 'demo', 'demo')
    >>> capabilities = client.capabilities()
    >>> print(capabilities)
    ...
    """

    """Defining property due to gRPC timeout being based on a C long type.
    Should really define this based on architecture.
    32-bit C long max value. "Infinity".
    """
    _C_MAX_LONG = 2147483647

    _NS_IN_S = int(1e9)

    def __init__(
        self,
        target,
        username,
        password,
        timeout=_C_MAX_LONG,
        credentials=None,
        credentials_from_file=False,
        tls_server_override=None,
        tls_enabled=True,
    ):
        """Initializes the gNMI gRPC client stub and defines auxiliary attributes.

        Parameters
        ----------
        target : str
            The host[:port] to issue gNMI requests against.
        username : str
        password : str
        timeout : uint, optional
            Timeout for request which sets a deadline for return.
            Defaults to "infinity"
        credentials : str, optional
            PEM contents or PEM file path.
        credentials_from_file : bool, optional
            Indicates that credentials is a file path.
        tls_server_override : str, optional
            TLS server name if PEM will not match.
            Please only utilize in testing.
        tls_enabled : bool, optional
            Whether or not to utilize a secure channel.
            If disabled, and functional, gNMI server is against specification.
        """
        self.username = username
        self.password = password
        self.timeout = int(timeout)
        self.tls_enabled = tls_enabled
        self.__target = util.gen_target(target)
        self.__credentials = util.gen_credentials(credentials, credentials_from_file)
        self.__options = util.gen_options(tls_server_override)
        self.__client = util.gen_client(
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

        Returns
        -------
        proto.gnmi_pb2.CapabilityResponse
        """
        message = proto.gnmi_pb2.CapabilityRequest()
        response = self.__client.Capabilities(message, metadata=self.__gen_metadata())
        return response

    def get(
        self,
        paths,
        prefix=None,
        data_type=proto.gnmi_pb2.GetRequest.DataType.ALL,
        encoding=proto.gnmi_pb2.Encoding.JSON_IETF,
        use_models=None,
        extension=None,
    ):
        """A snapshot of the requested data that exists on the target.

        Parameters
        ----------
        paths : iterable of proto.gnmi_pb2.Path
            An iterable of Paths to request data of.
        prefix : proto.gnmi_pb2.Path, optional
            A path to prefix all Paths in paths
        data_type : proto.gnmi_pb2.GetRequest.DataType, optional
            A member of the GetRequest.DataType enum to specify what datastore to target
            [ALL, CONFIG, STATE, OPERATIONAL]
        encoding : proto.gnmi_pb2.Encoding, optional
            A member of the proto.gnmi_pb2.Encoding enum specifying desired encoding of returned data
            [JSON, BYTES, PROTO, ASCII, JSON_IETF]
        use_models : iterable of proto.gnmi_pb2.ModelData, optional
        extension : iterable of proto.gnmi_ext.Extension, optional

        Returns
        -------
        proto.gnmi_pb2.GetResponse
        """
        data_type = util.validate_proto_enum(
            "data_type",
            data_type,
            "GetRequest.DataType",
            proto.gnmi_pb2.GetRequest.DataType,
        )
        encoding = util.validate_proto_enum(
            "encoding", encoding, "Encoding", proto.gnmi_pb2.Encoding
        )
        request = proto.gnmi_pb2.GetRequest()
        if not isinstance(paths, (list, set)):
            raise Exception("paths must be an iterable containing Path(s)!")
        for path in paths:
            request.path.append(path)
        request.type = data_type
        request.encoding = encoding
        if prefix:
            request.prefix = prefix
        if use_models:
            request.use_models = use_models
        if extension:
            request.extension = extension
        get_response = self.__client.Get(request, metadata=self.__gen_metadata())
        return get_response

    def set(
        self, prefix=None, updates=None, replaces=None, deletes=None, extensions=None
    ):
        """Modifications to the configuration of the target.

        Parameters
        ----------
        prefix : proto.gnmi_pb2.Path, optional
            The Path to prefix all other Paths defined within other messages
        updates : iterable of iterable of proto.gnmi_pb2.Update, optional
            The Updates to update configuration with.
        replaces : iterable of proto.gnmi_pb2.Update, optional
            The Updates which replaces other configuration.
            The main difference between replace and update is replace will remove non-referenced nodes.
        deletes : iterable of proto.gnmi_pb2.Path, optional
            The Paths which refers to elements for deletion.
        extensions : iterable of proto.gnmi_ext.Extension, optional

        Returns
        -------
        proto.gnmi_pb2.SetResponse
        """
        request = proto.gnmi_pb2.SetRequest()
        if prefix:
            request.prefix = prefix
        test_list = [updates, replaces, deletes]
        if not any(test_list):
            raise Exception("At least update, replace, or delete must be specified!")
        for item in test_list:
            if not item:
                continue
            if not isinstance(item, (list, set)):
                raise Exception("updates, replaces, and deletes must be iterables!")
        if updates:
            for update in updates:
                request.update.append(update)
        if replaces:
            for update in replaces:
                request.replace.append(update)
        if deletes:
            for path in deletes:
                request.delete.append(path)
        if extensions:
            for extension in extensions:
                request.extension.append(extension)
        response = self.__client.Set(request, metadata=self.__gen_metadata())
        return response

    def subscribe(self, request_iter, extensions=None):
        """Subscribe allows a client to request the target to send it values
        of particular paths within the data tree. These values may be streamed
        at a particular cadence (STREAM), sent one off on a long-lived channel
        (POLL), or sent as a one-off retrieval (ONCE).
        Reference: gNMI Specification Section 3.5

        Parameters
        ----------
        request_iter : iterable of proto.gnmi_pb2.SubscriptionList or proto.gnmi_pb2.Poll or proto.gnmi_pb2.AliasList
            The requests to embed as the SubscribeRequest, oneof the above.
            subscribe RPC is a streaming request thus can arbitrarily generate SubscribeRequests into request_iter
            to use the same bi-directional streaming connection if already open.
        extensions : iterable of proto.gnmi_ext.Extension, optional

        Returns
        -------
        generator of SubscriptionResponse
        """

        def validate_request(request):
            subscribe_request = proto.gnmi_pb2.SubscribeRequest()
            if isinstance(request, proto.gnmi_pb2.SubscriptionList):
                subscribe_request.subscribe.CopyFrom(request)
            elif isinstance(request, proto.gnmi_pb2.Poll):
                subscribe_request.poll.CopyFrom(request)
            elif isinstance(request, proto.gnmi_pb2.AliasList):
                subscribe_request.aliases.CopyFrom(request)
            else:
                raise Exception(
                    "request must be a SubscriptionList, Poll, or AliasList!"
                )
            if extensions:
                for extension in extensions:
                    subscribe_request.extensions.append(extension)
            return subscribe_request

        response_stream = self.__client.Subscribe(
            (validate_request(request) for request in request_iter),
            metadata=self.__gen_metadata(),
        )
        return response_stream
