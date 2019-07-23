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

import grpc
from .proto import gnmi_pb2_grpc
from .proto import gnmi_pb2
from . import json_format

from grpc.beta import implementations

class Client(object):
    """This class creates grpc calls using python.
    """

    """Defining property due to gRPC timeout being based on a C long type.
    Should really define this based on architecture.
    32-bit C long max value. "Infinity".
    """
    __C_MAX_LONG = 2147483647

    def __init__(self, target, username, password,
        timeout=__C_MAX_LONG,
        credentials=None,
        credentials_from_file=False,
        tls_server_override=None
    ):
        self.username = username
        self.password = password
        self.timeout = int(timeout)
        self.__target = self.__gen_target(target)
        self.__credentials = self.__gen_credentials(credentials, credentials_from_file)
        self.__options = self.__gen_options(tls_server_override)
        self.__client = self.__gen_client(
            self.__target, self.__credentials, self.__options
        )

    def __repr__(self):
        return '%s(Host = %s, Port = %s, User = %s, Password = %s, Timeout = %s)' % (
            self.__class__.__name__,
            self._host,
            self._port,
            self._metadata[0][1],
            self._metadata[1][1],
            self._timeout
        )

    def capabilities(self):
        """Capabilities allows the client to retrieve the set of capabilities that
        is supported by the target. This allows the target to validate the
        service version that is implemented and retrieve the set of models that
        the target supports. The models can then be specified in subsequent RPCs
        to restrict the set of data that is utilized.
        Reference: gNMI Specification Section 3.2
        """
        message = gnmi_pb2.CapabilityRequest()
        responses = self._stub.Capabilities(message, metadata=self._metadata)
        return responses
    
    def get(self, path, prefix=None, gnmi_type=None,
            encoding=0, user_models=None, extension=None):
        """
        A snapshot of the state that exists on the target
        :param path: A set of paths to request data snapshot
        :param prefix: a path that is applied to all paths
        :param gnmi_type: type of data requested [CONFIG, STATE, OPERATIONAL]
        :param encoding: Data format data comes out in 2=Proto, 0=JSON
        :param user_models: ModelData messages indicating the schema definition
        :param extension: a repeated field to carry gNMI extensions
        :type path:
        :type prefix:
        :type gnmi_type: string
        :type encoding: int
        :type user_models:
        :type extension:
        :return: Return the response object
        :rtype:
        """
        request = gnmi_pb2.GetRequest(
            path=path,
            prefix=prefix,
            type=gnmi_type,
            encoding=encoding,
            user_models=user_models,
            extension=extension)
        response = self._stub.Get(request, metadata=self._metadata)
        return response
    
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
        request = gnmi_pb2.SetRequest(
            prefix=prefix,
            update=update,
            replace=replace,
            delete=delete)
        response = self._stub.Set(request, metadata=self._metadata)
        return response
    
    def subscribe(self, subs, interval_seconds, encoding=2):
        """
        Subscription to receive updates relating to the state of data instances on a target
        :param subs: Subscription paths to subscribe to
        :param interval_seconds: Time of subscription path
        :param encoding: Defaults to Proto, 1, JSON
        :type subs: list
        :type interval_seconds: int
        :type encoding: int
        :return: Telemetry stream
        """
        subscriptions = []
        interval = interval_seconds * 1000000000 # convert to ns
        for sub in subs:
            pathelems = []
            for pathlevel in sub.split("/"):
                pathelems.append(gnmi_pb2.PathElem(name=pathlevel))
            path = gnmi_pb2.Path(elem=pathelems)
            subscriptions.append(gnmi_pb2.Subscription(path=path, sample_interval=interval, mode="SAMPLE"))
        sublist = gnmi_pb2.SubscriptionList(subscriptions=subscriptions,encoding=encoding)
        subreq = [gnmi_pb2.SubscribeRequest(subscribe=sublist)]
        stream = self._stub.Subscribe(subreq, metadata=self._metadata)
        for unit in stream:
            yield unit

    def connectivityhandler(self, callback):
        """Passing of a callback to monitor connectivety state updates.
        :param callback: A callback for monitoring
        :type: function
        """
        self._channel.subscribe(callback, True)
    
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
            raise ValueError("Unable to parse netloc from target URL %s!", target)
        if parsed_target.scheme:
            logging.debug("Scheme identified in target, ignoring and using netloc.")
        target_netloc = parsed_target.netloc
        if parsed_target.port is None:
            ported_target = "%s:%i" % (parsed_target.hostname, default_port)
            logging.debug("No target port detected, reassembled to %s.", ported_target)
            target_netloc = Client.__gen_target(ported_target)
        return target_netloc

    @staticmethod
    def __gen_client(target, credentials=None, options=None):
        """Instantiates and returns the NX-OS gRPC client stub
        over an insecure or secure channel.
        """
        client = None
        if not credentials:
            insecure_channel = grpc.insecure_channel(target)
            client = proto.gRPCConfigOperStub(insecure_channel)
        else:
            channel_creds = grpc.ssl_channel_credentials(credentials)
            secure_channel = grpc.secure_channel(target, channel_creds, options)
            client = proto.gRPCConfigOperStub(secure_channel)
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
    def __parse_xpath_to_json(xpath, namespace):
        """Parses an XPath to JSON representation, and appends
        namespace into the JSON request.
        """
        if not namespace:
            raise ValueError("Must include namespace if constructing from xpath!")
        xpath_dict = {}
        xpath_split = xpath.split("/")
        first = True
        for element in reversed(xpath_split):
            if first:
                xpath_dict[element] = {}
                first = False
            else:
                xpath_dict = {element: xpath_dict}
        xpath_dict["namespace"] = namespace
        return json.dumps(xpath_dict)

    @staticmethod
    def __validate_enum_arg(name, valid_options, message=None):
        """Construct error around enumeration validation."""
        if name not in valid_options:
            if not message:
                message = "%s must be one of %s" % (name, ", ".join(valid_options))
            raise ValueError(message)
