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
    flattened = {}
    for key, value in yang_json:
        ykey = "/{}".format(key)
        path, value = __flatten_yang_json_element(ykey, value)
        flattened[path] = value
    return flattened

def __flatten_yang_json_element(prefix, fields):
    flattened = []
    for key, value in fields.items():
        curr_path = "{}/{}".format(prefix, key)
        keys = {}
        values = {}
        if isinstance(value, dict):
            for _key, _value in value.items():
                if isinstance(_value, str):
                    try:
                        values[_key] = int(_value)
                    except ValueError:
                        keys[_key] = _value
                elif isinstance(_value, int):
                    values[_key] = _value
            


            return __flatten_yang_json_element(curr_path, value)
        if isinstance(value, list):
            keys, fields = __flatten_yang_json_element(curr_path, value)
        