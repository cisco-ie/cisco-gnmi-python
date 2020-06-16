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
    op_map = {
        proto.gnmi_pb2.GetResponse: _flatten_get_response,
        proto.gnmi_pb2.SubscribeResponse: _flatten_subscribe_response
    }
    identified = False
    for message_class, op in op_map.items():
        if isinstance(message, message_class):
            identified = True
            op(message)
    if not identified:
        raise Exception("Flatten not yet supported for message class!")

def _flatten_get_response(get_response):
    flattened_response = {}
    for notification in get_response.notification:
        _, xpath = parse_path_to_xpath(notification.path)
        value = 

def _flatten_subscribe_response(subscribe_response):
    pass

def _flatten_yang_json(yang_json):
    return __flatten_yang_json_element("", yang_json)

def __flatten_yang_json_element(prefix, fields, convert_strings=True):
    flattened = {}
    keys = {}
    values = {}
    to_traverse = {}
    if isinstance(fields, list):
        for elem in fields:
            flattened.update(__flatten_yang_json_element(prefix, elem))
    elif isinstance(fields, dict):
        for key, value in fields.items():
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
            flattened.update(__flatten_yang_json_element(keyed_elem, value, convert_strings))
        for key, value in values.items():
            keyed_elem = "{prefix}{keys}/{elem}".format(prefix=prefix, elem=key, keys=key_string)
            flattened[keyed_elem] = value
    return flattened
        