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
import json
import os

from six import string_types
from .client import Client, proto, util

logger = logging.getLogger(__name__)


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

    def xpath_to_path_elem(self, request):
        paths = []
        message = {
            'update': [],
            'replace': [],
            'delete': [],
            'get': [],
        }
        if 'nodes' not in request:
            # TODO: raw rpc?
            return paths
        else:
            namespace_modules = {}
            origin = 'DME'
            for prefix, nspace in request.get('namespace', {}).items():
                if '/Cisco-IOS-' in nspace:
                    module = nspace[nspace.rfind('/') + 1:]
                elif '/cisco-nx' in nspace: # NXOS lowercases namespace
                    module = 'Cisco-NX-OS-device'
                elif '/openconfig.net' in nspace:
                    module = 'openconfig-'
                    module += nspace[nspace.rfind('/') + 1:]
                elif 'urn:ietf:params:xml:ns:yang:' in nspace:
                    module = nspace.replace(
                        'urn:ietf:params:xml:ns:yang:', '')
                if module:
                    namespace_modules[prefix] = module

            for node in request.get('nodes', []):
                if 'xpath' not in node:
                    log.error('Xpath is not in message')
                else:
                    xpath = node['xpath']
                    value = node.get('value', '')
                    edit_op = node.get('edit-op', '')

                    for pfx, ns in namespace_modules.items():
                        # NXOS does not support prefixes yet so clear them out
                        if pfx in xpath and 'openconfig' in ns:
                            origin = 'openconfig'
                            xpath = xpath.replace(pfx + ':', '')
                            if isinstance(value, string_types):
                                value = value.replace(pfx + ':', '')
                        elif pfx in xpath and 'device' in ns:
                            origin = 'device'
                            xpath = xpath.replace(pfx + ':', '')
                            if isinstance(value, string_types):
                                value = value.replace(pfx + ':', '')
                    if edit_op:
                        if edit_op in ['create', 'merge', 'replace']:
                            xpath_lst = xpath.split('/')
                            name = xpath_lst.pop()
                            xpath = '/'.join(xpath_lst)
                            if edit_op == 'replace':
                                if not message['replace']:
                                    message['replace'] = [{
                                        xpath: {name: value}
                                    }]
                                else:
                                    message['replace'].append(
                                        {xpath: {name: value}}
                                    )
                            else:
                                if not message['update']:
                                    message['update'] = [{
                                        xpath: {name: value}
                                    }]
                                else:
                                    message['update'].append(
                                        {xpath: {name: value}}
                                    )
                        elif edit_op in ['delete', 'remove']:
                            if message['delete']:
                                message['delete'].add(xpath)
                            else:
                                message['delete'] = set(xpath)
                    else:
                        message['get'].append(xpath)
        return namespace_modules, message, origin

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

    def check_configs(self, configs):
        if isinstance(configs, string_types):
            logger.debug("Handling as JSON string.")
            try:
                configs = json.loads(configs)
            except:
                raise Exception("{0}\n is invalid JSON!".format(configs))
            configs = [configs]
        elif isinstance(configs, dict):
            logger.debug("Handling already serialized JSON object.")
            configs = [configs]
        elif not isinstance(configs, (list, set)):
            raise Exception(
                "{0} must be an iterable of configs!".format(str(configs))
            )
        return configs

    def create_updates(self, configs, origin, json_ietf=False):
        if not configs:
            return None
        configs = self.check_configs(configs)

        xpaths = []
        updates = []
        for config in configs:
            xpath = next(iter(config.keys()))
            xpaths.append(xpath)
        common_xpath = os.path.commonprefix(xpaths)

        if common_xpath:
            update_configs = self.get_payload(configs)
            for update_cfg in update_configs:
                xpath, payload = update_cfg
                update = proto.gnmi_pb2.Update()
                update.path.CopyFrom(
                    self.parse_xpath_to_gnmi_path(
                        xpath, origin=origin
                    )
                )
                if json_ietf:
                    update.val.json_ietf_val = payload
                else:
                    update.val.json_val = payload
                updates.append(update)
            return updates
        else:
            for config in configs:
                top_element = next(iter(config.keys()))
                update = proto.gnmi_pb2.Update()
                update.path.CopyFrom(self.parse_xpath_to_gnmi_path(top_element))
                config = config.pop(top_element)
                if json_ietf:
                    update.val.json_ietf_val = json.dumps(config).encode("utf-8")
                else:
                    update.val.json_val = json.dumps(config).encode("utf-8")
                updates.append(update)
            return updates

    def set_json(self, update_json_configs=None, replace_json_configs=None,
                 origin='device', json_ietf=False):
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
        origin : openconfig, device, or DME

        Returns
        -------
        set()
        """
        if not any([update_json_configs, replace_json_configs]):
            raise Exception("Must supply at least one set of configurations to method!")

        updates = self.create_updates(
            update_json_configs,
            origin=origin,
            json_ietf=json_ietf
        )
        replaces = self.create_updates(
            replace_json_configs,
            origin=origin,
            json_ietf=json_ietf
        )
        for update in updates + replaces:
            logger.info('\nGNMI set:\n{0}\n{1}'.format(9 * '=', str(update)))

        return self.set(updates=updates, replaces=replaces)

    def get_xpaths(self, xpaths, data_type="ALL",
                   encoding="JSON", origin='openconfig'):
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
            [JSON, JSON_IETF]

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
            gnmi_path = []
            for xpath in set(xpaths):
                gnmi_path.append(self.parse_xpath_to_gnmi_path(xpath, origin))
        elif isinstance(xpaths, string_types):
            gnmi_path = [self.parse_xpath_to_gnmi_path(xpaths, origin)]
        else:
            raise Exception(
                "xpaths must be a single xpath string or iterable of xpath strings!"
            )
        logger.info('GNMI get:\n{0}\n{1}'.format(9 * '=', str(gnmi_path)))
        return self.get(gnmi_path, data_type=data_type, encoding=encoding)

    def subscribe_xpaths(
        self,
        xpath_subscriptions,
        request_mode="STREAM",
        sub_mode="SAMPLE",
        encoding="PROTO",
        sample_interval=Client._NS_IN_S * 10,
        origin='openconfig'
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

        Returns
        -------
        subscribe()
        """
        supported_request_modes = ["STREAM", "ONCE", "POLL"]
        supported_encodings = ["JSON", "PROTO"]
        supported_sub_modes = ["ON_CHANGE", "SAMPLE"]
        subscription_list = proto.gnmi_pb2.SubscriptionList()
        subscription_list.mode = util.validate_proto_enum(
            "mode",
            request_mode,
            "SubscriptionList.Mode",
            proto.gnmi_pb2.SubscriptionList.Mode,
            supported_request_modes,
        )
        subscription_list.encoding = util.validate_proto_enum(
            "encoding",
            encoding,
            "Encoding",
            proto.gnmi_pb2.Encoding,
            supported_encodings,
        )
        if isinstance(xpath_subscriptions, string_types):
            xpath_subscriptions = [xpath_subscriptions]
        subscriptions = []
        for xpath_subscription in xpath_subscriptions:
            subscription = None
            if isinstance(xpath_subscription, string_types):
                subscription = proto.gnmi_pb2.Subscription()
                subscription.path.CopyFrom(
                    self.parse_xpath_to_gnmi_path(
                        xpath_subscription,
                        origin
                    )
                )
                subscription.mode = util.validate_proto_enum(
                    "sub_mode",
                    sub_mode,
                    "SubscriptionMode",
                    proto.gnmi_pb2.SubscriptionMode,
                    supported_sub_modes,
                )
                subscription.sample_interval = sample_interval
            elif isinstance(xpath_subscription, dict):
                path = self.parse_xpath_to_gnmi_path(
                    xpath_subscription["path"],
                    origin
                )
                arg_dict = {
                    "path": path,
                    "mode": sub_mode,
                    "sample_interval": sample_interval,
                }
                arg_dict.update(xpath_subscription)
                if "mode" in arg_dict:
                    arg_dict["mode"] = util.validate_proto_enum(
                        "sub_mode",
                        arg_dict["mode"],
                        "SubscriptionMode",
                        proto.gnmi_pb2.SubscriptionMode,
                        supported_sub_modes,
                    )
                subscription = proto.gnmi_pb2.Subscription(**arg_dict)
            elif isinstance(xpath_subscription, proto.gnmi_pb2.Subscription):
                subscription = xpath_subscription
            else:
                raise Exception("xpath in list must be xpath or dict/Path!")
            subscriptions.append(subscription)
        subscription_list.subscription.extend(subscriptions)
        logger.info('GNMI subscribe:\n{0}\n{1}'.format(
            15 * '=', str(subscription_list))
        )
        return self.subscribe([subscription_list])

    def parse_xpath_to_gnmi_path(self, xpath, origin):
        """Origin defaults to YANG (device) paths
        Otherwise specify "DME" as origin
        """
        if origin is None:
            if any(map(xpath.startswith, ["/Cisco-NX-OS-device", "/ietf-interfaces"])):
                origin = "device"
            else:
                origin = "DME"

        return super(NXClient, self).parse_xpath_to_gnmi_path(xpath, origin)
