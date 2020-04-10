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
from collections import OrderedDict
from xml.etree.ElementPath import xpath_tokenizer_re
import re
import json
import os
from six import string_types

from cisco_gnmi import proto
from cisco_gnmi import util


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

    def __init__(self, grpc_channel, timeout=_C_MAX_LONG):
        """gNMI initialization wrapper which simply wraps some aspects of the gNMI stub.

        Parameters
        ----------
        grpc_channel : grpc.Channel
            The gRPC channel to initialize the gNMI stub with.
            Use ClientBuilder if unfamiliar with gRPC.
        username : str
            Username to authenticate gNMI RPCs.
        password : str
            Password to authenticate gNMI RPCs.
        timeout : uint
            Timeout for gRPC functionality.
        """
        self.service = proto.gnmi_pb2_grpc.gNMIStub(grpc_channel)

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
        response = self.service.Capabilities(message)
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
        try:
            iter(paths)
        except TypeError:
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
        get_response = self.service.Get(request)
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
            request.update.extend(updates)
        if replaces:
            request.replaces.extend(replaces)
        if deletes:
            request.delete.extend(deletes)
        if extensions:
            request.extension.extend(extensions)
        response = self.service.Set(request)
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
            return subscribe_request

        response_stream = self.service.Subscribe(
            (validate_request(request) for request in request_iter)
        )
        return response_stream

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
        """Check configs, and construct "Update" messages.

        Parameters
        ----------
        configs: dict of <xpath>: <dict val for JSON>
        origin: str [DME, device, openconfig]
        json_ietf: bool encoding type for Update val (default False)

        Returns
        -------
        List of Update messages with val populated.

        If a set of configs contain a common Xpath, the Update must contain
        a consolidation of xpath/values for 2 reasons:

        1. Devices may have a restriction on how many Update messages it will
           accept at once.
        2. Some xpath/values are required to be set in same Update because of
           dependencies like leafrefs, mandatory settings, and if/when/musts.
        """
        if not configs:
            return []
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

    def parse_xpath_to_gnmi_path(self, xpath, origin=None):
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

    def combine_configs(self, payload, last_xpath, cfg):
        """Walking from end to finish 2 xpaths merge so combine them
                                   |--config
            |---last xpath config--|
        ----|                      |--config
            |
            |   pick these up -->  |--config
            |---this xpath config--|
                                   |--config
        Parameters
        ----------
        payload: dict of partial payload
        last_xpath: last xpath that was processed
        xpath: colliding xpath
        config: dict of values associated to colliding xpath
        """
        xpath, config, is_key = cfg
        lp = last_xpath.split('/')
        xp = xpath.split('/')
        base = []
        top = ''
        for i, seg in enumerate(zip(lp, xp)):
            if seg[0] != seg[1]:
                top = seg[1]
                break
        base = '/' + '/'.join(xp[i:])
        cfg = (base, config, False)
        extended_payload = {top: self.xpath_to_json([cfg])}
        payload.update(extended_payload)
        return payload

    def xpath_to_json(self, configs, last_xpath='', payload={}):
        """Try to combine Xpaths/values into a common payload (recursive).

        Parameters
        ----------
        configs: tuple of xpath/value dict
        last_xpath: str of last xpath that was recusivly processed.
        payload: dict being recursively built for JSON transformation.

        Returns
        -------
        dict of combined xpath/value dict.
        """
        for i, cfg in enumerate(configs, 1):
            xpath, config, is_key = cfg
            if last_xpath and xpath not in last_xpath:
                # Branched config here     |---config
                #   |---last xpath config--|
                # --|                      |---config
                #   |---this xpath config
                payload = self.combine_configs(payload, last_xpath, cfg)
                return self.xpath_to_json(configs[i:], xpath, payload)
            xpath_segs = xpath.split('/')
            xpath_segs.reverse()
            for seg in xpath_segs:
                if not seg:
                    continue
                if payload:
                    if is_key:
                        if seg in payload:
                            if isinstance(payload[seg], list):
                                payload[seg].append(config)
                            elif isinstance(payload[seg], dict):
                                payload[seg].update(config)
                        else:
                            payload.update(config)
                            payload = {seg: [payload]}
                    else:
                        config.update(payload)
                        payload = {seg: config}
                    return self.xpath_to_json(configs[i:], xpath, payload)
                else:
                    if is_key:
                        payload = {seg: [config]}
                    else:
                        payload = {seg: config}
                    return self.xpath_to_json(configs[i:], xpath, payload)
        return payload

    # Pattern to detect keys in an xpath
    RE_FIND_KEYS = re.compile(r'\[.*?\]')

    def get_payload(self, configs):
        """Common Xpaths were detected so try to consolidate them.

        Parameter
        ---------
        configs: tuple of xpath/value dicts
        """
        # Number of updates are limited so try to consolidate into lists.
        xpaths_cfg = []
        first_key = set()
        # Find first common keys for all xpaths_cfg of collection.
        for config in configs:
            xpath = next(iter(config.keys()))

            # Change configs to tuples (xpath, config) for easier management
            xpaths_cfg.append((xpath, config[xpath]))

            xpath_split = xpath.split('/')
            for seg in xpath_split:
                if '[' in seg:
                    first_key.add(seg)
                    break

        # Common first key/configs represents one GNMI update
        updates = []
        for key in first_key:
            update = []
            remove_cfg = []
            for config in xpaths_cfg:
                xpath, cfg = config
                if key in xpath:
                    update.append(config)
                else:
                    for k, v in cfg.items():
                        if '[{0}="{1}"]'.format(k, v) not in key:
                            break
                    else:
                        # This cfg sets the first key so we don't need it
                        remove_cfg.append((xpath, cfg))
            if update:
                for upd in update:
                    # Remove this config out of main list
                    xpaths_cfg.remove(upd)
                for rem_cfg in remove_cfg:
                    # Sets a key in update path so remove it
                    xpaths_cfg.remove(rem_cfg)
                updates.append(update)
                break

        # Add remaining configs to updates
        if xpaths_cfg:
            updates.append(xpaths_cfg)

        # Combine all xpath configs of each update if possible
        xpaths = []
        compressed_updates = []
        for update in updates:
            xpath_consolidated = {}
            config_compressed = []
            for seg in update:
                xpath, config = seg
                if xpath in xpath_consolidated:
                    xpath_consolidated[xpath].update(config)
                else:
                    xpath_consolidated[xpath] = config
                    config_compressed.append((xpath, xpath_consolidated[xpath]))
                    xpaths.append(xpath)

            # Now get the update path for this batch of configs
            common_xpath = os.path.commonprefix(xpaths)
            cfg_compressed = []
            keys = []

            # Need to reverse the configs to build the dict correctly
            config_compressed.reverse()
            for seg in config_compressed:
                is_key = False
                prepend_path = ''
                xpath, config = seg
                end_path = xpath[len(common_xpath):]
                if end_path.startswith('['):
                    # Don't start payload with a list
                    tmp = common_xpath.split('/')
                    prepend_path = '/' + tmp.pop()
                    common_xpath = '/'.join(tmp)
                end_path = prepend_path + end_path

                # Building json, need to identify configs that set keys
                for key in keys:
                    if [k for k in config.keys() if k in key]:
                        is_key = True
                keys += re.findall(self.RE_FIND_KEYS, end_path)
                cfg_compressed.append((end_path, config, is_key))

            update = (common_xpath, cfg_compressed)
            compressed_updates.append(update)

        updates = []
        for update in compressed_updates:
            common_xpath, cfgs = update
            payload = self.xpath_to_json(cfgs)
            updates.append(
                (
                    common_xpath,
                    json.dumps(payload).encode('utf-8')
                )
            )
        return updates

    def xml_path_to_path_elem(self, request):
        """Convert XML Path Language 1.0 Xpath to gNMI Path/PathElement.

        Modeled after YANG/NETCONF Xpaths.

        References:
        * https://www.w3.org/TR/1999/REC-xpath-19991116/#location-paths
        * https://www.w3.org/TR/1999/REC-xpath-19991116/#path-abbrev
        * https://tools.ietf.org/html/rfc6020#section-6.4
        * https://tools.ietf.org/html/rfc6020#section-9.13
        * https://tools.ietf.org/html/rfc6241

        Parameters
        ---------
        request: dict containing request namespace and nodes to be worked on.
            namespace: dict of <prefix>: <namespace>
            nodes: list of dict
                  <xpath>: Xpath pointing to resource
                  <value>: value to set resource to
                  <edit-op>: equivelant NETCONF edit-config operation

        Returns
        -------
        tuple: namespace_modules, message dict, origin
            namespace_modules: dict of <prefix>: <module name>
                Needed for future support.
            message dict: 4 lists containing possible updates, replaces,
                deletes, or gets derived form input nodes.
            origin str: DME, device, or openconfig
        """

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


if __name__ == '__main__':
    from pprint import pprint as pp
    import grpc
    from cisco_gnmi.auth import CiscoAuthPlugin
    channel = grpc.secure_channel(
        '127.0.0.1:9339',
        grpc.composite_channel_credentials(
            grpc.ssl_channel_credentials(),
            grpc.metadata_call_credentials(
                CiscoAuthPlugin(
                        'admin',
                        'its_a_secret'
                )
            )
        )
    )
    client = Client(channel)
    request = {
        'namespace': {
            'oc-acl': 'http://openconfig.net/yang/acl'
        },
        'nodes': [
            {
                'value': 'testacl',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set/name',
                'edit-op': 'merge'
            },
            {
                'value': 'ACL_IPV4',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set/type',
                'edit-op': 'merge'
            },
            {
                'value': '10',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set[name="testacl"][type="ACL_IPV4"]/oc-acl:acl-entries/oc-acl:acl-entry/oc-acl:sequence-id',
                'edit-op': 'merge'
            },
            {
                'value': '20.20.20.1/32',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set[name="testacl"][type="ACL_IPV4"]/oc-acl:acl-entries/oc-acl:acl-entry[sequence-id="10"]/oc-acl:ipv4/oc-acl:config/oc-acl:destination-address',
                'edit-op': 'merge'
            },
            {
                'value': 'IP_TCP',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set[name="testacl"][type="ACL_IPV4"]/oc-acl:acl-entries/oc-acl:acl-entry[sequence-id="10"]/oc-acl:ipv4/oc-acl:config/oc-acl:protocol',
                'edit-op': 'merge'
            },
            {
                'value': '10.10.10.10/32',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set[name="testacl"][type="ACL_IPV4"]/oc-acl:acl-entries/oc-acl:acl-entry[sequence-id="10"]/oc-acl:ipv4/oc-acl:config/oc-acl:source-address',
                'edit-op': 'merge'
            },
            {
                'value': 'DROP',
                'xpath': '/oc-acl:acl/oc-acl:acl-sets/oc-acl:acl-set[name="testacl"][type="ACL_IPV4"]/oc-acl:acl-entries/oc-acl:acl-entry[sequence-id="10"]/oc-acl:actions/oc-acl:config/oc-acl:forwarding-action',
                'edit-op': 'merge'
            }
        ]
    }
    modules, message, origin = client.xml_path_to_path_elem(request)
    pp(modules)
    pp(message)
    pp(origin)
    """
    # Expected output
    =================
    {'oc-acl': 'openconfig-acl'}
    {'delete': [],
    'get': [],
    'replace': [],
    'update': [{'/acl/acl-sets/acl-set': {'name': 'testacl'}},
                {'/acl/acl-sets/acl-set': {'type': 'ACL_IPV4'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry': {'sequence-id': '10'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'destination-address': '20.20.20.1/32'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'protocol': 'IP_TCP'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'source-address': '10.10.10.10/32'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/actions/config': {'forwarding-action': 'DROP'}}]}
    'openconfig'
    """
    # Feed converted XML Path Language 1.0 Xpaths to create updates
    updates = client.create_updates(message['update'], origin)
    pp(updates)
    """
    # Expected output
    =================
    [path {
    origin: "openconfig"
    elem {
        name: "acl"
    }
    elem {
        name: "acl-sets"
    }
    elem {
        name: "acl-set"
        key {
        key: "name"
        value: "testacl"
        }
        key {
        key: "type"
        value: "ACL_IPV4"
        }
    }
    elem {
        name: "acl-entries"
    }
    }
    val {
    json_val: "{\"acl-entry\": [{\"actions\": {\"config\": {\"forwarding-action\": \"DROP\"}}, \"ipv4\": {\"config\": {\"destination-address\": \"20.20.20.1/32\", \"protocol\": \"IP_TCP\", \"source-address\": \"10.10.10.10/32\"}}, \"sequence-id\": \"10\"}]}"
    }
    ]
    # update is now ready to be sent through gNMI SetRequest
    """
