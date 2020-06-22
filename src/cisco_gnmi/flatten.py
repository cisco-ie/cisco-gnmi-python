"""Copyright 2020 Cisco Systems
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

"""Helper functions to flatten nested gNMI message data.
e.g. "/interfaces/interface[name=HundredGigE0/0/0/12]/state/counters/in-broadcast-pkts": 0
"""
import json
import logging
from . import proto


def flatten(message, convert_strings=True, ignore_delete=True, origin_as_module=False):
    """Top level convenience function which accepts a protobuf
    message and indirects to the appropriate handler function to
    flatten the data to a simple, flat xpath:value dict representation.
    Currently only handles GetResponse and SubscribeResponse.
    """
    flatten_method_map = {
        proto.gnmi_pb2.GetResponse: _flatten_get_response,
        proto.gnmi_pb2.SubscribeResponse: _flatten_subscribe_response,
    }
    identified = False
    flattened_message = None
    for message_class, flatten_method in flatten_method_map.items():
        if isinstance(message, message_class):
            identified = True
            flattened_message = flatten_method(
                message, convert_strings, ignore_delete, origin_as_module
            )
    if not identified:
        raise Exception("Flatten not yet supported for message class!")
    return flattened_message


def flatten_yang_json(prefix, yang_json, convert_strings=True, implicit_keys=True):
    """Flattens a JSON structure with special consideration
    around strings - inlining like keys and attempting integer
    conversion given the uint64-as-string JSON encoding rules.
    Recursive implementation, many dict updates, not intensely validated.
    """
    flattened = {}
    keys = {}
    values = {}
    to_traverse = {}
    if isinstance(yang_json, list):
        for elem in yang_json:
            flattened.update(flatten_yang_json(prefix, elem))
    elif isinstance(yang_json, dict):
        for key, value in yang_json.items():
            if isinstance(value, str):
                potential_key = False
                if convert_strings:
                    try:
                        values[key] = int(value)
                    except ValueError:
                        try:
                            values[key] = float(value)
                        except ValueError:
                            potential_key = True
                else:
                    potential_key = True
                if potential_key and implicit_keys:
                    keys[key] = value
                else:
                    values[key] = value
            # Fun fact, boolean is a sub of int in Python
            elif isinstance(value, bool) and implicit_keys:
                keys[key] = json.dumps(value)
            elif isinstance(value, (int, float)):
                values[key] = value
            elif isinstance(value, (dict, list)):
                to_traverse[key] = value
            else:
                raise Exception("Unhandled element type!")
        key_string = ""
        for key, value in keys.items():
            key_string += "[{key}={value}]".format(key=key, value=value)
        for key, value in to_traverse.items():
            keyed_elem = "{prefix}{keys}/{elem}".format(
                prefix=prefix, elem=key, keys=key_string
            )
            flattened.update(flatten_yang_json(keyed_elem, value, convert_strings))
        for key, value in values.items():
            keyed_elem = "{prefix}{keys}/{elem}".format(
                prefix=prefix, elem=key, keys=key_string
            )
            flattened[keyed_elem] = value
    return flattened


def parse_path_to_xpath(path):
    """Parses a gNMI Path to XPath equivalent."""
    origin = path.origin
    xpath = ""
    for elem in path.elem:
        xpath += "/{}".format(elem.name)
        for key in elem.key:
            xpath += "[{}={}]".format(key, elem.key[key])
    return origin, xpath


def _flatten_get_response(
    get_response, convert_strings=True, ignore_delete=True, origin_as_module=False
):
    flattened_response = {}
    for notification in get_response.notification:
        flattened_response.update(
            __flatten_notification(
                notification, convert_strings, ignore_delete, origin_as_module
            )
        )
    return flattened_response


def _flatten_subscribe_response(
    subscribe_response, convert_strings=True, ignore_delete=True, origin_as_module=False
):
    return __flatten_notification(
        subscribe_response.update, convert_strings, ignore_delete, origin_as_module
    )


def __flatten_notification(
    notification_message,
    convert_strings=True,
    ignore_delete=True,
    origin_as_module=False,
):
    flattened_response = {}
    origin, xpath_prefix = parse_path_to_xpath(notification_message.prefix)
    # This is to accomodate IOS XR/NX-OS reporting module as origin
    if origin_as_module is True and origin:
        xpath_prefix = "/{}:{}".format(origin, xpath_prefix.strip("/"))

    def __realize_xpath(_prefix, _suffix):
        _xpath = ""
        if _prefix and _suffix:
            template_str = (
                "{}{}" if _prefix.endswith("/") or _suffix.startswith("/") else "{}/{}"
            )
            _xpath = template_str.format(_prefix, _suffix)
        elif _prefix:
            _xpath = _prefix
        elif _suffix:
            _xpath = _suffix
        return _xpath

    for update in notification_message.update:
        _origin, xpath_update = parse_path_to_xpath(update.path)
        # TODO: Janky logic
        if origin and _origin:
            raise Exception("Double origin? {} and {}.".format(origin, _origin))
        elif not origin and origin_as_module is True:
            xpath_update = "/{}:{}".format(_origin, xpath_update.strip("/"))
        xpath = __realize_xpath(xpath_prefix, xpath_update)
        value_name = update.val.WhichOneof("value")
        update_value = getattr(update.val, value_name)
        if value_name in {"json_val", "json_ietf_val"}:
            serialized_json = None
            try:
                json_content = update_value.decode("utf-8")
                serialized_json = json.loads(json_content)
            except json.decoder.JSONDecodeError as e:
                logging.error(json_content)
                raise e
            sub_flattened_response = flatten_yang_json(
                xpath, serialized_json, convert_strings
            )
            flattened_response.update(sub_flattened_response)
        else:
            flattened_response[xpath] = update_value
    if not ignore_delete:
        for path in notification_message.delete:
            _origin, xpath_delete = parse_path_to_xpath(path)
            # TODO: Janky logic
            if origin and _origin:
                raise Exception("Double origin? {} and {}.".format(origin, _origin))
            elif not origin and origin_as_module is True:
                xpath_delete = "/{}:{}".format(_origin, xpath_delete.strip("/"))
            xpath = __realize_xpath(xpath_prefix, xpath_delete)
            if xpath in flattened_response.keys():
                raise Exception("Deleted element in update messages!")
            flattened_response[xpath] = None
    return flattened_response
