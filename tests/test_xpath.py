import json
from src.cisco_gnmi import xpath_util


def test_parse_xpath_to_gnmi_path():
    result = xpath_util.parse_xpath_to_gnmi_path(
        '/acl/acl-sets/acl-set',
        origin='openconfig'
    )
    assert str(result) == GNMI_UPDATE_ACL_SET


def test_combine_configs():
    pass


def test_xpath_to_json():
    pass


def test_get_payload():
    result = xpath_util.get_payload(PARSE_XPATH_TO_GNMI[1]['update'])
    xpath, config = result[0]
    assert xpath == '/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries'
    # json_val
    cfg = json.loads(config)
    assert cfg == {
        'acl-entry': [
            {
                'config': {'forwarding-action': 'DROP'},
                'ipv4': {'config': {'destination-address': '20.20.20.1/32',
                                    'protocol': 'IP_TCP',
                                    'source-address': '10.10.10.10/32'}
                },
                'sequence-id': '10'
            }
        ]
    }


def test_xml_path_to_path_elem():
    result = xpath_util.xml_path_to_path_elem(XML_PATH_LANGUAGE_1)
    assert result == (
        {'oc-acl': 'openconfig-acl'},  # module
        {  # config
            'delete': [],
            'get': [],
            'replace': [],
            'update': [
                {'/acl/acl-sets/acl-set': {'name': 'testacl'}},
                {'/acl/acl-sets/acl-set': {'type': 'ACL_IPV4'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry': {'sequence-id': '10'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'destination-address': '20.20.20.1/32'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'protocol': 'IP_TCP'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'source-address': '10.10.10.10/32'}},
                {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/actions/config': {'forwarding-action': 'DROP'}}
            ]
        },
        'openconfig'  # origin
    )


XML_PATH_LANGUAGE_1 = {
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


PARSE_XPATH_TO_GNMI = (
    {'oc-acl': 'openconfig-acl'},  # module
    {  # config
        'delete': [],
        'get': [],
        'replace': [],
        'update': [
            {'/acl/acl-sets/acl-set': {'name': 'testacl'}},
            {'/acl/acl-sets/acl-set': {'type': 'ACL_IPV4'}},
            {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry': {'sequence-id': '10'}},
            {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'destination-address': '20.20.20.1/32'}},
            {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'protocol': 'IP_TCP'}},
            {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/ipv4/config': {'source-address': '10.10.10.10/32'}},
            {'/acl/acl-sets/acl-set[name="testacl"][type="ACL_IPV4"]/acl-entries/acl-entry[sequence-id="10"]/actions/config': {'forwarding-action': 'DROP'}}
        ]
    },
    'openconfig'  # origin
)


GNMI_UPDATE_ACL_ENTRY = """[path {
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
"""


GNMI_UPDATE_ACL_SET = """origin: "openconfig"
elem {
  name: "acl"
}
elem {
  name: "acl-sets"
}
elem {
  name: "acl-set"
}
"""
