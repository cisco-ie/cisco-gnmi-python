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
            request.replace.extend(replaces)
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

    def subscribe_xpaths(
        self,
        xpath_subscriptions,
        request_mode="STREAM",
        sub_mode="SAMPLE",
        encoding="JSON",
        sample_interval=_NS_IN_S * 10,
        suppress_redundant=False,
        heartbeat_interval=None,
        prefix=None,
    ):
        """A convenience wrapper of subscribe() which aids in building of SubscriptionRequest
        with request as subscribe SubscriptionList. This method accepts an iterable of simply xpath strings,
        dictionaries with Subscription attributes for more granularity, or already built Subscription
        objects and builds the SubscriptionList. Fields not supplied will be defaulted with the default arguments
        to the method.

        Generates a single SubscribeRequest.

        Parameters
        ----------
        xpath_subscriptions : str or iterable of str, dict, Subscription
            An iterable which is parsed to form the Subscriptions in the SubscriptionList to be passed
            to SubscriptionRequest. Strings are parsed as XPaths and defaulted with the default arguments,
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
            A member of the proto.gnmi_pb2.Encoding enum specifying desired encoding of returned data
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
        prefix : proto.gnmi_pb2.Path, optional
            A common path prepended to all path elements in the message. This reduces message size by
            removing redundent path elements. Smaller message == improved thoughput.

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
        if prefix:
            subscription_list.prefix.CopyFrom(prefix)
        if isinstance(
            xpath_subscriptions, (string_types, dict, proto.gnmi_pb2.Subscription)
        ):
            xpath_subscriptions = [xpath_subscriptions]
        subscriptions = []
        for xpath_subscription in xpath_subscriptions:
            subscription = None
            if isinstance(xpath_subscription, proto.gnmi_pb2.Subscription):
                subscription = xpath_subscription
            elif isinstance(xpath_subscription, string_types):
                subscription = proto.gnmi_pb2.Subscription()
                subscription.path.CopyFrom(
                    self.parse_xpath_to_gnmi_path(xpath_subscription)
                )
                subscription.mode = util.validate_proto_enum(
                    "sub_mode",
                    sub_mode,
                    "SubscriptionMode",
                    proto.gnmi_pb2.SubscriptionMode,
                )
                if sub_mode == "SAMPLE":
                    subscription.sample_interval = sample_interval
            elif isinstance(xpath_subscription, dict):
                subscription_dict = {}
                if "path" not in xpath_subscription.keys():
                    raise Exception("path must be specified in dict!")
                if isinstance(xpath_subscription["path"], proto.gnmi_pb2.Path):
                    subscription_dict["path"] = xpath_subscription["path"]
                elif isinstance(xpath_subscription["path"], string_types):
                    subscription_dict["path"] = self.parse_xpath_to_gnmi_path(
                        xpath_subscription["path"]
                    )
                else:
                    raise Exception("path must be string or Path proto!")
                sub_mode_name = (
                    sub_mode
                    if "mode" not in xpath_subscription.keys()
                    else xpath_subscription["mode"]
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
                        if "sample_interval" not in xpath_subscription.keys()
                        else xpath_subscription["sample_interval"]
                    )
                    if "suppress_redundant" in xpath_subscription.keys():
                        subscription_dict["suppress_redundant"] = xpath_subscription[
                            "suppress_redundant"
                        ]
                if sub_mode_name != "TARGET_DEFINED":
                    if "heartbeat_interval" in xpath_subscription.keys():
                        subscription_dict["heartbeat_interval"] = xpath_subscription[
                            "heartbeat_interval"
                        ]
                subscription = proto.gnmi_pb2.Subscription(**subscription_dict)
            else:
                raise Exception("path must be string, dict, or Subscription proto!")
            subscriptions.append(subscription)
        subscription_list.subscription.extend(subscriptions)
        return self.subscribe([subscription_list])

    @classmethod
    def parse_xpath_to_gnmi_path(cls, xpath, origin=None):
        """Parses an XPath to proto.gnmi_pb2.Path.
        This function should be overridden by any child classes for origin logic.

        Effectively wraps the std XML XPath tokenizer and traverses
        the identified groups. Parsing robustness needs to be validated.
        Probably best to formalize as a state machine sometime.
        TODO: Formalize tokenizer traversal via state machine.
        """
        if not isinstance(xpath, string_types):
            raise Exception("xpath must be a string!")
        path = proto.gnmi_pb2.Path()
        if origin:
            if not isinstance(origin, string_types):
                raise Exception("origin must be a string!")
            path.origin = origin
        curr_elem = proto.gnmi_pb2.PathElem()
        in_filter = False
        just_filtered = False
        curr_key = None
        # TODO: Lazy
        xpath = xpath.strip("/")
        xpath_elements = xpath_tokenizer_re.findall(xpath)
        path_elems = []
        for index, element in enumerate(xpath_elements):
            # stripped initial /, so this indicates a completed element
            if element[0] == "/":
                if not curr_elem.name:
                    raise Exception(
                        "Current PathElem has no name yet is trying to be pushed to path! Invalid XPath?"
                    )
                path_elems.append(curr_elem)
                curr_elem = proto.gnmi_pb2.PathElem()
                continue
            # We are entering a filter
            elif element[0] == "[":
                in_filter = True
                continue
            # We are exiting a filter
            elif element[0] == "]":
                in_filter = False
                continue
            # If we're not in a filter then we're a PathElem name
            elif not in_filter:
                curr_elem.name = element[1]
            # Skip blank spaces
            elif not any([element[0], element[1]]):
                continue
            # If we're in the filter and just completed a filter expr,
            # "and" as a junction should just be ignored.
            elif in_filter and just_filtered and element[1] == "and":
                just_filtered = False
                continue
            # Otherwise we're in a filter and this term is a key name
            elif curr_key is None:
                curr_key = element[1]
                continue
            # Otherwise we're an operator or the key value
            elif curr_key is not None:
                # I think = is the only possible thing to support with PathElem syntax as is
                if element[0] in [">", "<"]:
                    raise Exception("Only = supported as filter operand!")
                if element[0] == "=":
                    continue
                else:
                    # We have a full key here, put it in the map
                    if curr_key in curr_elem.key.keys():
                        raise Exception("Key already in key map!")
                    curr_elem.key[curr_key] = element[0].strip("'\"")
                    curr_key = None
                    just_filtered = True
        # Keys/filters in general should be totally cleaned up at this point.
        if curr_key:
            raise Exception("Hanging key filter! Incomplete XPath?")
        # If we have a dangling element that hasn't been completed due to no
        # / element then let's just append the final element.
        if curr_elem:
            path_elems.append(curr_elem)
            curr_elem = None
        if any([curr_elem, curr_key, in_filter]):
            raise Exception("Unfinished elements in XPath parsing!")
        path.elem.extend(path_elems)
        return path
