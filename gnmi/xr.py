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

"""Wrapper for IOS XR to simplify usage of gNMI implementation."""

import json
import logging

from .client import Client, proto, util


class XRClient(Client):
    """IOS XR-specific wrapper for gNMI functionality."""

    def set_json(
        self,
        update_json_configs=None,
        replace_json_configs=None,
        delete_json_configs=None,
        ietf=True,
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
        delete_json_configs : iterable of JSON configurations, optional
            JSON configs to apply as deletions.
        ietf : bool, optional
            Use JSON_IETF vs JSON.

        Returns
        -------
        set()
        """
        if not any([update_json_configs, replace_json_configs, delete_json_configs]):
            raise Exception("Must supply at least one set of configurations to method!")

        def check_configs(name, configs):
            if isinstance(name, str):
                logging.debug("Handling %s as JSON string.", name)
                try:
                    configs = json.loads(configs)
                except:
                    raise Exception("{name} is invalid JSON!".format(name=name))
                configs = [configs]
            elif isinstance(name, dict):
                logging.debug("Handling %s as already serialized JSON object.", name)
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
                top_element_split = top_element.split(":")
                if len(top_element_split) < 2:
                    raise Exception(
                        "Top level config element {} should be module prefixed!".format(
                            top_element
                        )
                    )
                elif len(top_element_split) > 2:
                    raise Exception(
                        "Top level config element {} appears malformed!".format(
                            top_element
                        )
                    )
                origin = top_element_split[0]
                element = top_element_split[1]
                config = config.pop(top_element)
                update = proto.gnmi_pb2.Update()
                update.path.CopyFrom(util.parse_xpath_to_gnmi_path(element, origin))
                if ietf:
                    update.val.json_ietf_val = json.dumps(config).encode("utf-8")
                else:
                    update.val.json_val = json.dumps(config).encode("utf-8")
                updates.append(update)
            return updates

        updates = create_updates("update_json_configs", update_json_configs)
        replaces = create_updates("replace_json_configs", replace_json_configs)
        deletes = create_updates("delete_json_configs", delete_json_configs)
        return self.set(updates=updates, replaces=replaces, deletes=deletes)

    def get_xpaths(self, xpaths, data_type="ALL", encoding="JSON_IETF"):
        """A convenience wrapper for get() which forms proto.gnmi_pb2.Path from supplied xpaths.

        Parameters
        ----------
        xpaths : iterable of str or str
            An iterable of XPath strings to request data of
            If simply a str, wraps as a list for convenience
        data_type : proto.gnmi_pb2.GetRequest.DataType, optional
            A direct value or key from the GetRequest.DataType enum
        encoding : proto.gnmi_pb2.GetRequest.Encoding, optional
            A direct value or key from the Encoding enum

        Returns
        -------
        get()
        """
        gnmi_path = None
        if isinstance(xpaths, (list, set)):
            gnmi_path = map(util.parse_xpath_to_gnmi_path, set(xpaths))
        elif isinstance(xpaths, str):
            gnmi_path = [util.parse_xpath_to_gnmi_path(xpaths)]
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
        sample_interval=Client._NS_IN_S,
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
            Default nanoseconds for sample to occur.
            Defaults to 5 seconds.
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
        if isinstance(xpath_subscriptions, str):
            xpath_subscriptions = [xpath_subscriptions]
        for xpath_subscription in xpath_subscriptions:
            subscription = None
            if isinstance(xpath_subscription, str):
                subscription = proto.gnmi_pb2.Subscription()
                subscription.path.CopyFrom(
                    util.parse_xpath_to_gnmi_path(xpath_subscription)
                )
                subscription.mode = util.validate_proto_enum(
                    "sub_mode",
                    sub_mode,
                    "SubscriptionMode",
                    proto.gnmi_pb2.SubscriptionMode,
                )
                subscription.sample_interval = sample_interval
                subscription.suppress_redundant = suppress_redundant
                if heartbeat_interval:
                    subscription.heartbeat_interval = heartbeat_interval
            elif isinstance(xpath_subscription, dict):
                path = util.parse_xpath_to_gnmi_path(xpath_subscription["path"])
                arg_dict = {
                    "path": path,
                    "mode": sub_mode,
                    "sample_interval": sample_interval,
                    "suppress_redundant": suppress_redundant,
                }
                if heartbeat_interval:
                    arg_dict["heartbeat_interval"] = heartbeat_interval
                arg_dict.update(xpath_subscription)
                if "mode" in arg_dict:
                    arg_dict["mode"] = util.validate_proto_enum(
                        "sub_mode",
                        arg_dict["mode"],
                        "SubscriptionMode",
                        proto.gnmi_pb2.SubscriptionMode,
                    )
                subscription = proto.gnmi_pb2.Subscription(**arg_dict)
            elif isinstance(xpath_subscription, proto.gnmi_pb2.Subscription):
                subscription = xpath_subscription
            else:
                raise Exception("xpath in list must be xpath or dict/Path!")
            subscription_list.subscription.append(subscription)
        return self.subscribe([subscription_list])
