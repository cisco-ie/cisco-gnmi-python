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

import json
import logging

from six import string_types
from .client import Client, proto, util


LOGGER = logging.getLogger(__name__)
logger = LOGGER


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

    def delete_xpaths(self, xpaths, prefix=None):
        """A convenience wrapper for set() which constructs Paths from supplied xpaths
        to be passed to set() as the delete parameter.

        Parameters
        ----------
        xpaths : iterable of str
            XPaths to specify to be deleted.
            If prefix is specified these strings are assumed to be the suffixes.
        prefix : str
            The XPath prefix to apply to all XPaths for deletion.

        Returns
        -------
        set()
        """
        if isinstance(xpaths, string_types):
            xpaths = [xpaths]
        paths = []
        # prefix is not supported on NX yet
        prefix = None
        for xpath in xpaths:
            if prefix:
                if prefix.endswith("/") and xpath.startswith("/"):
                    xpath = "{prefix}{xpath}".format(
                        prefix=prefix[:-1], xpath=xpath[1:]
                    )
                elif prefix.endswith("/") or xpath.startswith("/"):
                    xpath = "{prefix}{xpath}".format(prefix=prefix, xpath=xpath)
                else:
                    xpath = "{prefix}/{xpath}".format(prefix=prefix, xpath=xpath)
            paths.append(self.parse_xpath_to_gnmi_path(xpath))
        return self.set(deletes=paths)

    def set_json(
        self,
        update_json_configs=None,
        replace_json_configs=None,
        ietf=False,
        prefix=None,
    ):
        """A convenience wrapper for set() which assumes JSON payloads and constructs desired messages.
        All parameters are optional, but at least one must be present.

        This method expects JSON in the same format as what you might send via the native gRPC interface
        with a fully modeled configuration which is then parsed to meet the gNMI implementation.

        Parameters
        ----------
        update_json_configs : iterable of JSON configurations, optional
            JSON configs to apply as updates.
        replace_json_configs : iterable of JSON configurations, optional
            JSON configs to apply as replacements.
        ietf : bool, optional
            Use JSON_IETF vs JSON.
        prefix : proto.gnmi_pb2.Path, optional
            A common path prepended to all path elements in the message. This reduces message size by
            removing redundent path elements. Smaller message == improved thoughput.

        Returns
        -------
        set()
        """
        # JSON_IETF and prefix are not supported on NX yet
        ietf = False
        prefix = None

        if not any([update_json_configs, replace_json_configs]):
            raise Exception("Must supply at least one set of configurations to method!")

        def check_configs(name, configs):
            if isinstance(configs, string_types):
                logger.debug("Handling %s as JSON string.", name)
                try:
                    configs = json.loads(configs)
                except:
                    raise Exception("{name} is invalid JSON!".format(name=name))
                configs = [configs]
            elif isinstance(configs, dict):
                logger.debug("Handling %s as already serialized JSON object.", name)
                configs = [configs]
            elif not isinstance(configs, (list, set)):
                raise Exception(
                    "{name} must be an iterable of configs!".format(name=name)
                )
            return configs

        def create_updates(name, configs):
            if not configs:
                return None
            configs = check_configs(name, configs)
            updates = []
            for config in configs:
                if not isinstance(config, dict):
                    raise Exception("config must be a JSON object!")
                if len(config.keys()) > 1:
                    raise Exception("config should only target one YANG module!")
                top_element = next(iter(config.keys()))
                update = proto.gnmi_pb2.Update()
                update.path.CopyFrom(self.parse_xpath_to_gnmi_path(top_element))
                config = config.pop(top_element)
                if ietf:
                    update.val.json_ietf_val = json.dumps(config).encode("utf-8")
                else:
                    update.val.json_val = json.dumps(config).encode("utf-8")
                updates.append(update)
            return updates

        updates = create_updates("update_json_configs", update_json_configs)
        replaces = create_updates("replace_json_configs", replace_json_configs)
        return self.set(prefix=prefix, updates=updates, replaces=replaces)

    def get_xpaths(self, xpaths, data_type="ALL", encoding="JSON"):
        """A convenience wrapper for get() which forms proto.gnmi_pb2.Path from supplied xpaths.

        Parameters
        ----------
        xpaths : iterable of str or str
            An iterable of XPath strings to request data of
            If simply a str, wraps as a list for convenience
        data_type : proto.gnmi_pb2.GetRequest.DataType, optional
            A direct value or key from the GetRequest.DataType enum
            [ALL, CONFIG, STATE, OPERATIONAL]
        encoding : proto.gnmi_pb2.GetRequest.Encoding, optional
            A direct value or key from the Encoding enum
            [JSON] is only setting supported at this time

        Returns
        -------
        get()
        """
        supported_encodings = ["JSON"]
        encoding = util.validate_proto_enum(
            "encoding",
            encoding,
            "Encoding",
            proto.gnmi_pb2.Encoding,
            supported_encodings,
        )
        gnmi_path = None
        if isinstance(xpaths, (list, set)):
            gnmi_path = map(self.parse_xpath_to_gnmi_path, set(xpaths))
        elif isinstance(xpaths, string_types):
            gnmi_path = [self.parse_xpath_to_gnmi_path(xpaths)]
        else:
            raise Exception(
                "xpaths must be a single xpath string or iterable of xpath strings!"
            )
        return self.get(gnmi_path, data_type=data_type, encoding=encoding)

    def subscribe_xpaths(
        self,
        xpath_subscriptions,
        request_mode="STREAM",
        sub_mode="SAMPLE",
        encoding="PROTO",
        sample_interval=Client._NS_IN_S * 10,
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
        prefix: proto.Path, optional
            Prefix path that can be used as a general path to prepend to all Path elements. (not supported on NX)

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
            prefix,
        )

    @classmethod
    def parse_xpath_to_gnmi_path(cls, xpath, origin=None):
        """Attempts to determine whether origin should be YANG (device) or DME.
        """
        if origin is None:
            if any(
                map(
                    xpath.startswith,
                    [
                        "Cisco-NX-OS-device",
                        "/Cisco-NX-OS-device",
                        "cisco-nx-os-device",
                        "/cisco-nx-os-device",
                    ],
                )
            ):
                origin = "device"
                # Remove the module
                xpath = xpath.split(":", 1)[1]
            else:
                origin = "openconfig"
        return super(NXClient, cls).parse_xpath_to_gnmi_path(xpath, origin)
