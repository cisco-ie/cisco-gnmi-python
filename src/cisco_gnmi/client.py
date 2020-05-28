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

import logging
from xml.etree.ElementPath import xpath_tokenizer_re
from six import string_types

from . import proto
from . import util
from . import path as path_helper


LOGGER = logging.getLogger(__name__)
logger = LOGGER


class Client(object):
    """gNMI gRPC wrapper client to ease usage of gNMI.

    Returns relatively raw response data. Response data may be accessed according
    to the gNMI specification.

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
    >>> import grpc
    >>> from cisco_gnmi import Client
    >>> from cisco_gnmi.auth import CiscoAuthPlugin
    >>> channel = grpc.secure_channel(
    ...     '127.0.0.1:9339',
    ...     grpc.composite_channel_credentials(
    ...         grpc.ssl_channel_credentials(),
    ...         grpc.metadata_call_credentials(
    ...             CiscoAuthPlugin(
    ...                  'admin',
    ...                  'its_a_secret'
    ...             )
    ...         )
    ...     )
    ... )
    >>> client = Client(channel)
    >>> capabilities = client.capabilities()
    >>> print(capabilities)
    """

    """Defining property due to gRPC timeout being based on a C long type.
    Should really define this based on architecture.
    32-bit C long max value. "Infinity".
    """
    _C_MAX_LONG = 2147483647

    # gNMI uses nanoseconds, baseline to seconds
    _NS_IN_S = int(1e9)

    def __init__(self, grpc_channel, timeout=_C_MAX_LONG, default_call_metadata=None):
        """gNMI initialization wrapper which simply wraps some aspects of the gNMI stub.

        Parameters
        ----------
        grpc_channel : grpc.Channel
            The gRPC channel to initialize the gNMI stub with.
            Use ClientBuilder if unfamiliar with gRPC.
        timeout : uint
            Timeout for gRPC functionality.
        default_call_metadata : list
            Metadata to be sent with each gRPC call.
        """
        self.service = proto.gnmi_pb2_grpc.gNMIStub(grpc_channel)
        self.default_call_metadata = default_call_metadata
        self._channel = grpc_channel

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
        LOGGER.debug(str(message))
        response = self.service.Capabilities(
            message, metadata=self.default_call_metadata
        )
        return response

    def get(
        self,
        paths,
        prefix=None,
        data_type="ALL",
        encoding="JSON_IETF",
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
        if not isinstance(paths, (list, set, map)):
            raise Exception("paths must be an iterable containing Path(s)!")
        request.path.extend(paths)
        request.type = data_type
        request.encoding = encoding
        if prefix:
            request.prefix = prefix
        if use_models:
            request.use_models = use_models
        if extension:
            request.extension = extension

        LOGGER.debug(str(request))

        get_response = self.service.Get(request, metadata=self.default_call_metadata)
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
            request.prefix.CopyFrom(prefix)
        test_list = [updates, replaces, deletes]
        if not any(test_list):
            raise Exception("At least update, replace, or delete must be specified!")
        for item in test_list:
            if not item:
                continue
            if not isinstance(item, (list, set)):
                raise Exception("updates, replaces, and deletes must be iterables!")
        if updates:
            request.update.extend(updates)
        if replaces:
            request.replaces.extend(replaces)
        if deletes:
            request.delete.extend(deletes)
        if extensions:
            request.extension.extend(extensions)

        LOGGER.debug(str(request))

        response = self.service.Set(request, metadata=self.default_call_metadata)
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
                subscribe_request.extensions.extend(extensions)

            LOGGER.debug(str(subscribe_request))

            return subscribe_request

        response_stream = self.service.Subscribe(
            (validate_request(request) for request in request_iter),
            metadata=self.default_call_metadata,
        )
        return response_stream

    def subscribe_paths(
        self,
        path_subscriptions,
        request_mode="STREAM",
        sub_mode="SAMPLE",
        encoding="JSON",
        sample_interval=_NS_IN_S * 10,
        suppress_redundant=False,
        heartbeat_interval=None,
    ):
        """A convenience wrapper of subscribe() which aids in building of SubscriptionRequest
        with request as subscribe SubscriptionList. This method accepts an iterable of path (xpath-like) strings,
        dictionaries with Subscription attributes for more granularity, or already built Subscription
        objects and builds the SubscriptionList. Fields not supplied will be defaulted with the default arguments
        to the method.

        Generates a single SubscribeRequest.

        Parameters
        ----------
        path_subscriptions : str or iterable of str, dict, Subscription
            An iterable which is parsed to form the Subscriptions in the SubscriptionList to be passed
            to SubscriptionRequest. Strings are parsed as XPath-like and defaulted with the default arguments,
            dictionaries are treated as dicts of args to pass to the Subscribe init, and Subscription is
            treated as simply a pre-made Subscription.
        request_mode : proto.gnmi_pb2.SubscriptionList.Mode, optional
            Indicates whether STREAM to stream from target,
            ONCE to stream once (like a get),
            POLL to respond to POLL.
            [STREAM, ONCE, POLL]
        sub_mode : proto.gnmi_pb2.SubscriptionMode, optional
            The default SubscriptionMode on a per Subscription basis in the SubscriptionList.
            TARGET_DEFINED indicates that the target (like device/destination) should stream
            information however it knows best. This instructs the target to decide between ON_CHANGE
            or SAMPLE - e.g. the device gNMI server may understand that we only need RIB updates
            as an ON_CHANGE basis as opposed to SAMPLE, and we don't have to explicitly state our
            desired behavior.
            ON_CHANGE only streams updates when changes occur.
            SAMPLE will stream the subscription at a regular cadence/interval.
            [TARGET_DEFINED, ON_CHANGE, SAMPLE]
        encoding : proto.gnmi_pb2.Encoding, optional
            A member of the proto.gnmi_pb2.Encoding enum specifying desired encoding of returned data.
            Defaults to JSON per specification.
            [JSON, BYTES, PROTO, ASCII, JSON_IETF]
        sample_interval : int, optional
            Default nanoseconds for SAMPLE to occur.
            Defaults to 10 seconds.
        suppress_redundant : bool, optional
            Indicates whether values that have not changed should be sent in a SAMPLE subscription.
        heartbeat_interval : int, optional
            Specifies the maximum allowable silent period in nanoseconds when
            suppress_redundant is in use. The target should send a value at least once
            in the period specified. Also applies in ON_CHANGE.

        Returns
        -------
        subscribe()
        """
        subscription_list = proto.gnmi_pb2.SubscriptionList()
        subscription_list.mode = util.validate_proto_enum(
            "mode",
            request_mode,
            "SubscriptionList.Mode",
            proto.gnmi_pb2.SubscriptionList.Mode,
        )
        subscription_list.encoding = util.validate_proto_enum(
            "encoding", encoding, "Encoding", proto.gnmi_pb2.Encoding
        )
        if isinstance(
            path_subscriptions, (string_types, dict, proto.gnmi_pb2.Subscription)
        ):
            path_subscriptions = [path_subscriptions]
        subscriptions = []
        for path_subscription in path_subscriptions:
            subscription = None
            if isinstance(path_subscription, proto.gnmi_pb2.Subscription):
                subscription = path_subscription
            elif isinstance(path_subscription, string_types):
                subscription = proto.gnmi_pb2.Subscription()
                subscription.path.CopyFrom(
                    self.parse_path_to_gnmi_path(path_subscription)
                )
                subscription.mode = util.validate_proto_enum(
                    "sub_mode",
                    sub_mode,
                    "SubscriptionMode",
                    proto.gnmi_pb2.SubscriptionMode,
                )
                if sub_mode == "SAMPLE":
                    subscription.sample_interval = sample_interval
            elif isinstance(path_subscription, dict):
                subscription_dict = {}
                if "path" not in path_subscription.keys():
                    raise Exception("path must be specified in dict!")
                if isinstance(path_subscription["path"], proto.gnmi_pb2.Path):
                    subscription_dict["path"] = path_subscription["path"]
                elif isinstance(path_subscription["path"], string_types):
                    subscription_dict["path"] = self.parse_path_to_gnmi_path(
                        path_subscription["path"]
                    )
                else:
                    raise Exception("path must be string or Path proto!")
                sub_mode_name = (
                    sub_mode
                    if "mode" not in path_subscription.keys()
                    else path_subscription["mode"]
                )
                subscription_dict["mode"] = util.validate_proto_enum(
                    "sub_mode",
                    sub_mode,
                    "SubscriptionMode",
                    proto.gnmi_pb2.SubscriptionMode,
                )
                if sub_mode_name == "SAMPLE":
                    subscription_dict["sample_interval"] = (
                        sample_interval
                        if "sample_interval" not in path_subscription.keys()
                        else path_subscription["sample_interval"]
                    )
                    if "suppress_redundant" in path_subscription.keys():
                        subscription_dict["suppress_redundant"] = path_subscription[
                            "suppress_redundant"
                        ]
                if sub_mode_name != "TARGET_DEFINED":
                    if "heartbeat_interval" in path_subscription.keys():
                        subscription_dict["heartbeat_interval"] = path_subscription[
                            "heartbeat_interval"
                        ]
                subscription = proto.gnmi_pb2.Subscription(**subscription_dict)
            else:
                raise Exception("path must be string, dict, or Subscription proto!")
            subscriptions.append(subscription)
        subscription_list.subscription.extend(subscriptions)
        return self.subscribe([subscription_list])

    def subscribe_xpaths(self, xpath_subscriptions, *args, **kwargs):
        """Compatibility with earlier versions.
        Use subscribe_paths.
        """
        return self.subscribe_paths(xpath_subscriptions, *args, **kwargs)

    def parse_path_to_gnmi_path(self, path, origin=None):
        return path_helper.parse_path_to_gnmi_path(path, origin)
