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

"""Wrapper for NX-OS to simplify usage of gNMI implementation."""


import logging

from six import string_types
from .client import Client, proto, util


class NXClient(Client):
    """NX-OS-specific wrapper for gNMI functionality.

    Returns direct responses from base Client methods.

    Methods
    -------
    subscribe_xpaths(...)
        Convenience wrapper for subscribe() which helps construct subscriptions for specified xpaths.

    Examples
    --------
    >>> from cisco_gnmi import ClientBuilder
    >>> client = ClientBuilder('127.0.0.1:9339').set_os(
    ...     'NX-OS'
    ... ).set_secure_from_file().set_ssl_target_override().set_call_authentication(
    ...     'admin',
    ...     'its_a_secret'
    ... ).construct()
    >>> capabilities = client.capabilities()
    >>> print(capabilities)
    """

    def get(self, *args, **kwargs):
        raise NotImplementedError("Get not yet supported on NX-OS!")

    def set(self, *args, **kwargs):
        raise NotImplementedError("Set not yet supported on NX-OS!")

    def subscribe_xpaths(
        self,
        xpath_subscriptions,
        request_mode="STREAM",
        sub_mode="SAMPLE",
        encoding="PROTO",
        sample_interval=Client._NS_IN_S * 10,
        suppress_redundant=False,
        heartbeat_interval=None,
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
            ON_CHANGE only streams updates when changes occur.
            SAMPLE will stream the subscription at a regular cadence/interval.
            [ON_CHANGE, SAMPLE]
        encoding : proto.gnmi_pb2.Encoding, optional
            A member of the proto.gnmi_pb2.Encoding enum specifying desired encoding of returned data
            [JSON, PROTO]
        sample_interval : int, optional
            Default nanoseconds for sample to occur.
            Defaults to 10 seconds.
        suppress_redundant : bool, optional
            Indicates whether values that have not changed should be sent in a SAMPLE subscription.
        heartbeat_interval : int, optional
            Specifies the maximum allowable silent period in nanoseconds when
            suppress_redundant is in use. The target should send a value at least once
            in the period specified.

        Returns
        -------
        subscribe()
        """
        supported_request_modes = ["STREAM", "ONCE", "POLL"]
        request_mode = util.validate_proto_enum(
            "mode",
            request_mode,
            "SubscriptionList.Mode",
            proto.gnmi_pb2.SubscriptionList.Mode,
            subset=supported_request_modes,
            return_name=True,
        )
        supported_encodings = ["JSON", "PROTO"]
        encoding = util.validate_proto_enum(
            "encoding",
            encoding,
            "Encoding",
            proto.gnmi_pb2.Encoding,
            subset=supported_encodings,
            return_name=True,
        )
        supported_sub_modes = ["ON_CHANGE", "SAMPLE"]
        sub_mode = util.validate_proto_enum(
            "sub_mode",
            sub_mode,
            "SubscriptionMode",
            proto.gnmi_pb2.SubscriptionMode,
            subset=supported_sub_modes,
            return_name=True,
        )
        return super(NXClient, self).subscribe_xpaths(
            xpath_subscriptions,
            request_mode,
            sub_mode,
            encoding,
            sample_interval,
            suppress_redundant,
            heartbeat_interval,
        )

    def parse_xpath_to_gnmi_path(self, xpath, origin=None):
        """Attempts to determine whether origin should be YANG (device) or DME.
        Errors on OpenConfig until support is present.
        """
        if xpath.startswith("openconfig"):
            raise NotImplementedError(
                "OpenConfig data models not yet supported on NX-OS!"
            )
        if origin is None:
            if any(
                map(xpath.startswith, ["Cisco-NX-OS-device", "/Cisco-NX-OS-device"])
            ):
                origin = "device"
                # Remove the module
                xpath = xpath.split(":", 1)[1]
            else:
                origin = "DME"
        return super(NXClient, self).parse_xpath_to_gnmi_path(xpath, origin)
