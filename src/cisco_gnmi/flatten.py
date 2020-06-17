import json
import logging
from . import proto

def parse_path_to_xpath(path):
    origin = path.origin
    xpath = ""
    for elem in path.elem:
        xpath += "/{}".format(elem.name)
        for key in elem.key:
            xpath += "[{}={}]".format(key, elem.key[key])
    return origin, xpath

def flatten(message, convert_strings=True, ignore_delete=True):
    flatten_method_map = {
        proto.gnmi_pb2.GetResponse: _flatten_get_response,
        proto.gnmi_pb2.SubscribeResponse: _flatten_subscribe_response
    }
    identified = False
    flattened_message = None
    for message_class, flatten_method in flatten_method_map.items():
        if isinstance(message, message_class):
            identified = True
            flattened_message = flatten_method(message, convert_strings, ignore_delete)
    if not identified:
        raise Exception("Flatten not yet supported for message class!")
    return flattened_message

def _flatten_get_response(get_response, convert_strings=True, ignore_delete=True):
    flattened_response = {}
    for notification in get_response.notification:
        flattened_response.update(__flatten_notification(notification))
    return flattened_response

def _flatten_subscribe_response(subscribe_response, convert_strings=True, ignore_delete=True):
    return __flatten_notification(subscribe_response.update)

def __flatten_notification(notification_message, convert_strings=True, ignore_delete=True):
    flattened_response = {}
    _, xpath_prefix = parse_path_to_xpath(notification_message.prefix)
    def __realize_xpath(_prefix, _suffix):
        _xpath = ""
        if _prefix and _suffix:
            _xpath = "{}/{}".format(_prefix, _suffix)
        elif _prefix:
            _xpath = _prefix
        elif _suffix:
            _xpath = _suffix
        return _xpath
    for update in notification_message.update:
        _, xpath_update = parse_path_to_xpath(update.path)
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
            sub_flattened_response = flatten_yang_json(xpath, serialized_json, convert_strings)
            flattened_response.update(sub_flattened_response)
        else:
            flattened_response[xpath] = update_value
    if not ignore_delete:
        for path in notification_message.delete:
            _, xpath_delete = parse_path_to_xpath(path)
            xpath = __realize_xpath(xpath_prefix, xpath_delete)
            if xpath in flattened_response.keys():
                raise Exception("Deleted element in update messages!")
            flattened_response[xpath] = None
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
        