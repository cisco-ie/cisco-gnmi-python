from xml.etree.ElementPath import xpath_tokenizer_re
from six import string_types

from . import proto

def parse_path_to_gnmi_path(path, origin=None):
    """Indirection method for parsing gNMI paths based upon
    origin.
    """
    gnmi_path = None
    if origin == "DME":
        gnmi_path = parse_dn_to_gnmi_path(path)
    else:
        gnmi_path = parse_xpath_to_gnmi_path(path)
    return gnmi_path

def parse_xpath_to_gnmi_path(xpath, origin=None):
    """Parses an XPath to proto.gnmi_pb2.Path.

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


def parse_dn_to_gnmi_path(dn, origin="DME"):
    """Parses a DME DN to proto.gnmi_pb2.Path.
    NX-OS oriented.
    """
    if not isinstance(dn, string_types):
        raise Exception("DN must be a string!")
    path = proto.gnmi_pb2.Path()
    if origin:
        if not isinstance(origin, string_types):
            raise Exception("Origin must be a string!")
        path.origin = origin
    curr_elem = proto.gnmi_pb2.PathElem()
    in_filter = False
    just_filtered = False
    curr_key = None
    curr_key_operator_found = False
    curr_key_val = None
    # TODO: Lazy
    dn = dn.strip("/")
    dn_elements = xpath_tokenizer_re.findall(dn)
    path_elems = []
    for index, element in enumerate(dn_elements):
        # stripped initial /, so this indicates a completed element
        if element[0] == "/":
            if not curr_elem.name:
                raise Exception(
                    "Current PathElem has no name yet is trying to be pushed to path! Invalid DN?"
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
            curr_elem.key[curr_key] = curr_key_val
            curr_key = None
            curr_key_operator_found = False
            curr_key_val = None
            in_filter = False
            continue
        # If we're not in a filter then we're a PathElem name
        elif not in_filter:
            curr_elem.name = element[1]
        # Skip blank spaces
        elif not any([element[0], element[1]]):
            continue
        # Otherwise we're in a filter and this term is a key name
        elif curr_key is None:
            curr_key = element[1]
            continue
        # Otherwise we're an operator or the key value
        elif curr_key is not None:
            if element[0] == "=" and not curr_key_operator_found:
                curr_key_operator_found = True
                continue
            elif curr_key_operator_found:
                if not curr_key_val:
                    curr_key_val = ""
                if element[0]:
                    curr_key_val += element[0]
                if element[1]:
                    curr_key_val += element[1]
            else:
                raise Exception("Entered unexpected DN key state!")
    # Keys/filters in general should be totally cleaned up at this point.
    if curr_key:
        raise Exception("Hanging key filter! Incomplete DN?")
    # If we have a dangling element that hasn't been completed due to no
    # / element then let's just append the final element.
    if curr_elem:
        path_elems.append(curr_elem)
        curr_elem = None
    if any([curr_elem, curr_key, in_filter]):
        raise Exception("Unfinished elements in DN parsing!")
    path.elem.extend(path_elems)
    return path

def parse_cli_to_gnmi_path(command):
    """Parses a CLI command to proto.gnmi_pb2.Path.
    IOS XR appears to be the only OS with this functionality.

    The CLI command becomes a path element.
    """
    if not isinstance(command, string_types):
        raise Exception("command must be a string!")
    path = proto.gnmi_pb2.Path()
    curr_elem = proto.gnmi_pb2.PathElem()
    curr_elem.name = command
    path.elem.extend([curr_elem])
    return path