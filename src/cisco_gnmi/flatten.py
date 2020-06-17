import json
from . import proto

def parse_path_to_xpath(path):
    origin = path.origin
    xpath = ""
    for elem in path.elem:
        xpath += "/{}".format(elem.name)
        for key in elem.key:
            xpath += "[{}={}]".format(key, elem.key[key])
    return origin, xpath

def flatten(message):
    flatten_method_map = {
        proto.gnmi_pb2.GetResponse: _flatten_get_response
    }
    identified = False
    flattened_message = None
    for message_class, flatten_method in flatten_method_map.items():
        if isinstance(message, message_class):
            identified = True
            flattened_message = flatten_method(message)
    if not identified:
        raise Exception("Flatten not yet supported for message class!")
    return flattened_message

def _flatten_get_response(get_response):
    flattened_response = {}
    for notification in get_response.notification:
        _, xpath_prefix = parse_path_to_xpath(notification.prefix)
        for update in notification.update:
            _, xpath_update = parse_path_to_xpath(update.path)
            xpath = ""
            if xpath_prefix and xpath_update:
                xpath = "{}/{}".format(xpath_prefix, xpath_update)
            elif xpath_prefix:
                xpath = xpath_prefix
            elif xpath_update:
                xpath = xpath_update
            update_name = update.WhichOneOf("value")
            update_value = getattr(update, update_name)
            if update_name in {"json_val", "json_ietf_val"}:
                raw_json = getattr(update, update_name)
                serialized_json = json.load(raw_json)
                sub_flattened_response = flatten_yang_json(xpath, serialized_json)
                flattened_response.update(sub_flattened_response)
            else:
                flattened_response[xpath] = update_value
    return flattened_response

def flatten_yang_json(prefix, yang_json, convert_strings=True):
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
                if convert_strings:
                    try:
                        values[key] = int(value)
                    except ValueError:
                        try:
                            values[key] = float(value)
                        except ValueError:
                            keys[key] = value
                else:
                    keys[key] = value
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
            keyed_elem = "{prefix}{keys}/{elem}".format(prefix=prefix, elem=key, keys=key_string)
            flattened.update(flatten_yang_json(keyed_elem, value, convert_strings))
        for key, value in values.items():
            keyed_elem = "{prefix}{keys}/{elem}".format(prefix=prefix, elem=key, keys=key_string)
            flattened[keyed_elem] = value
    return flattened
        