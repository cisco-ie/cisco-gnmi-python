import os
import re
import json
import logger
from xml.etree.ElementPath import xpath_tokenizer_re
from six import string_types
from cisco_gnmi import proto


log = logging.getLogger(__name__)


def parse_xpath_to_gnmi_path(xpath, origin=None):
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


def combine_configs(payload, last_xpath, cfg):
    """Walking from end to finish, 2 xpaths merge, so combine them.
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
    extended_payload = {top: xpath_to_json([cfg])}
    payload.update(extended_payload)
    return payload


def xpath_to_json(configs, last_xpath='', payload={}):
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
            payload = combine_configs(payload, last_xpath, cfg)
            return xpath_to_json(configs[i:], xpath, payload)
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
                return xpath_to_json(configs[i:], xpath, payload)
            else:
                if is_key:
                    payload = {seg: [config]}
                else:
                    payload = {seg: config}
                return xpath_to_json(configs[i:], xpath, payload)
    return payload


# Pattern to detect keys in an xpath
RE_FIND_KEYS = re.compile(r'\[.*?\]')


def get_payload(configs):
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
            keys += re.findall(RE_FIND_KEYS, end_path)
            cfg_compressed.append((end_path, config, is_key))

        update = (common_xpath, cfg_compressed)
        compressed_updates.append(update)

    updates = []
    for update in compressed_updates:
        common_xpath, cfgs = update
        payload = xpath_to_json(cfgs)
        updates.append(
            (
                common_xpath,
                json.dumps(payload).encode('utf-8')
            )
        )
    return updates


def xml_path_to_path_elem(request):
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
    from cisco_gnmi.client import Client

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
    modules, message, origin = xml_path_to_path_elem(request)
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
