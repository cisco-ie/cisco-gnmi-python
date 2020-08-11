# cisco-gnmi-python
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

This library wraps gNMI functionality to ease usage with Cisco implementations in Python programs. Derived from [openconfig/gnmi](https://github.com/openconfig/gnmi/tree/master/proto).

**This is not an officially supported Cisco product.** This library is intended to serve as a gNMI client reference implementation and streamline development with Cisco products.

- [cisco-gnmi-python](#cisco-gnmi-python)
  - [Usage](#usage)
    - [cisco-gnmi CLI](#cisco-gnmi-cli)
    - [ClientBuilder](#clientbuilder)
      - [Initialization Examples](#initialization-examples)
    - [Client](#client)
    - [NXClient](#nxclient)
    - [XEClient](#xeclient)
    - [XRClient](#xrclient)
  - [gNMI](#gnmi)
  - [Development](#development)
    - [Get Source](#get-source)
    - [Code Hygiene](#code-hygiene)
    - [Recompile Protobufs](#recompile-protobufs)
  - [CLI Usage](#cli-usage)
    - [Capabilities](#capabilities)
      - [Usage](#usage-1)
      - [Output](#output)
    - [Get](#get)
      - [Usage](#usage-2)
      - [Output](#output-1)
    - [Set](#set)
      - [Usage](#usage-3)
      - [Output](#output-2)
    - [Subscribe](#subscribe)
      - [Usage](#usage-4)
      - [Output](#output-3)
  - [Licensing](#licensing)
  - [Issues](#issues)
  - [Related Projects](#related-projects)

## Usage
```bash
pip install cisco-gnmi
python -c "import cisco_gnmi; print(cisco_gnmi)"
cisco-gnmi --help
```

This library covers the gNMI defined `Capabilities`, `Get`, `Set`, and `Subscribe` RPCs, and helper clients provide OS-specific recommendations. A CLI (`cisco-gnmi`) is also available upon installation. As commonalities and differences are identified between OS functionality this library will be refactored as necessary.

Several examples of library usage are available in [`examples/`](examples/). The `cisco-gnmi` CLI script found at [`src/cisco_gnmi/cli.py`](src/cisco_gnmi/cli.py) may also be useful.

It is *highly* recommended that users of the library learn [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) syntax to significantly ease usage. Understanding how to read Protocol Buffers, and reference [`gnmi.proto`](https://github.com/openconfig/gnmi/blob/master/proto/gnmi/gnmi.proto), will be immensely useful for utilizing gNMI and any other gRPC interface.

### cisco-gnmi CLI
Since `v1.0.5` a gNMI CLI is available as `cisco-gnmi` when this module is installed. `Capabilities`, `Get`, rudimentary `Set`, and `Subscribe` are supported. The CLI may be useful for simply interacting with a Cisco gNMI service, and also serves as a reference for how to use this `cisco_gnmi` library. CLI usage is documented at the bottom of this README in [CLI Usage](#cli-usage).

### ClientBuilder
Since `v1.0.0` a builder pattern is available with `ClientBuilder`. `ClientBuilder` provides several `set_*` methods which define the intended `Client` connectivity and a `construct` method to construct and return the desired `Client`. There are several major methods involved here:

```
    set_target(...)
        Specifies the network element to build a client for.
    set_os(...)
        Specifies which OS wrapper to deliver.
    set_secure(...)
        Specifies that a secure gRPC channel should be used.
    set_secure_from_file(...)
        Loads certificates from file system for secure gRPC channel.
    set_secure_from_target(...)
        Attempts to utilize available certificate from target for secure gRPC channel.
    set_call_authentication(...)
        Specifies username/password to utilize for authentication.
    set_ssl_target_override(...)
        Sets the gRPC option to override the SSL target name.
    set_channel_option(...)
        Sets a gRPC channel option. Implies knowledge of channel options.
    construct()
        Constructs and returns the built Client.
```

#### Initialization Examples
`ClientBuilder` can be chained for initialization or instantiated line-by-line.

```python
from cisco_gnmi import ClientBuilder

builder = ClientBuilder('127.0.0.1:9339')
builder.set_os('IOS XR')
builder.set_secure_from_target()
builder.set_call_authentication('admin', 'its_a_secret')
client = builder.construct()

# Or...

client = ClientBuilder('127.0.0.1:9339').set_os('IOS XR').set_secure_from_target().set_call_authentication('admin', 'its_a_secret').construct()
```

Using an encrypted channel automatically getting the certificate from the device, quick for testing:

```python
from cisco_gnmi import ClientBuilder

client = ClientBuilder(
    '127.0.0.1:9339'
).set_os('IOS XR').set_secure_from_target().set_call_authentication(
    'admin',
    'its_a_secret'
).construct()
```

Using an owned root certificate on the filesystem:

```python
from cisco_gnmi import ClientBuilder

client = ClientBuilder(
    '127.0.0.1:9339'
).set_os('IOS XR').set_secure_from_file(
    'ems.pem'
).set_call_authentication(
    'admin',
    'its_a_secret'
).construct()
```

Passing certificate content to method:

```python
from cisco_gnmi import ClientBuilder

# Note reading as bytes
with open('ems.pem', 'rb') as cert_fd:
    root_cert = cert_fd.read()

client = ClientBuilder(
    '127.0.0.1:9339'
).set_os('IOS XR').set_secure(
    root_cert
).set_call_authentication(
    'admin',
    'its_a_secret'
).construct()
```

Usage with root certificate, private key, and cert chain:

```python
from cisco_gnmi import ClientBuilder

client = ClientBuilder(
    '127.0.0.1:9339'
).set_os('IOS XE').set_secure_from_file(
    root_certificates='rootCA.pem',
    private_key='client.key',
    certificate_chain='client.crt',
).set_call_authentication(
    'admin',
    'its_a_secret'
).construct()
```


### Client
`Client` is a very barebones class simply implementing `capabilities`, `get`, `set`, and `subscribe` methods. It provides some context around the expectation for what should be supplied to these RPC functions and helpers for validation.

Methods are documented in [`src/cisco_gnmi/client.py`](src/cisco_gnmi/client.py).

### NXClient
`NXClient` inherits from `Client` and provides several wrapper methods which aid with NX-OS gNMI implementation usage. These are `subscribe_xpaths`, and the removal of `get` and `set` as they are not yet supported operations. These methods have some helpers and constraints around what is supported by the implementation.

Methods and usage examples are documented in [`src/cisco_gnmi/nx.py`](src/cisco_gnmi/nx.py).

### XEClient
`XEClient` inherits from `Client` and provides several wrapper methods which aid with IOS XE gNMI implementation usage. These are `delete_xpaths`, `get_xpaths`, `set_json`, and `subscribe_xpaths`. These methods have some helpers and constraints around what is supported by the implementation.

Methods and usage examples are documented in [`src/cisco_gnmi/xe.py`](src/cisco_gnmi/xe.py).

### XRClient
`XRClient` inherits from `Client` and provides several wrapper methods which aid with IOS XR gNMI implementation usage. These are `delete_xpaths`, `get_xpaths`, `set_json`, and `subscribe_xpaths`. These methods have some helpers and constraints around what is supported by the implementation.

Methods and usage examples are documented in [`src/cisco_gnmi/xr.py`](src/cisco_gnmi/xr.py).

## gNMI
gRPC Network Management Interface (gNMI) is a service defining an interface for a network management system (NMS) to interact with a network element. It may be thought of as akin to NETCONF or other control protocols which define operations and behaviors. The scope of gNMI is relatively simple - it seeks to "[[define](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md)] a gRPC-based protocol for the modification and retrieval of configuration from a target device, as well as the control and generation of telemetry streams from a target device to a data collection system. The intention is that a single gRPC service definition can cover both configuration and telemetry - allowing a single implementation on the target, as well as a single NMS element to interact with the device via telemetry and configuration RPCs".

gNMI is a specification developed by [OpenConfig](https://openconfig.net), an operator-driven working-group. It is important to note that gNMI only defines a protocol of behavior - not data models. This is akin to SNMP/MIBs and NETCONF/YANG. SNMP and NETCONF are respectively decoupled from the data itself in MIBs and YANG modules. gNMI is a control protocol, not a standardization of data. OpenConfig does develop standard data models as well, and does have some specialized behavior with OpenConfig originating models, but the data models themselves are out of the scope of gNMI.

## Development
Requires Python and utilizes `pipenv` for environment management. Manual usage of `pip`/`virtualenv` is not covered. Uses `black` for code formatting and `pylint` for code linting. `black` is not explicitly installed as it requires Python 3.6+.

### Get Source
```bash
git clone https://github.com/cisco-ie/cisco-gnmi-python.git
cd cisco-gnmi-python
# If pipenv not installed, install!
pip install --user pipenv
# Now use Makefile...
make setup
# Or pipenv manually if make not present
pipenv --three install --dev
# Enter virtual environment
pipenv shell
# Work work
exit
```

### Code Hygiene
We use [`black`](https://github.com/ambv/black) for code formatting and [`pylint`](https://www.pylint.org/) for code linting. `hygiene.sh` will run `black` against all of the code under `gnmi/` except for `protoc` compiled protobufs, and run `pylint` against Python files directly under `gnmi/`. They don't totally agree, so we're not looking for perfection here. `black` is not automatically installed due to requiring Python 3.6+. `hygiene.sh` will check for regular path availability and via `pipenv`, and otherwise falls directly to `pylint`. If `black` usage is desired, please install it into `pipenv` if using Python 3.6+ or separate methods e.g. `brew install black`.

```bash
# If using Python 3.6+
pipenv install --dev black
# Otherwise...
./hygiene.sh
```

### Recompile Protobufs
If a new `gnmi.proto` definition is released, use `update_protos.sh` to recompile. If breaking changes are introduced the wrapper library must be updated.

```bash
./update_protos.sh
```

## CLI Usage
The below details the current `cisco-gnmi` usage options. Please note that `Set` operations may be destructive to operations and should be tested in lab conditions.

```
cisco-gnmi --help
usage:
cisco-gnmi <rpc> [<args>]

Supported RPCs:
capabilities
subscribe
get
set

cisco-gnmi capabilities 127.0.0.1:57500
cisco-gnmi get 127.0.0.1:57500
cisco-gnmi set 127.0.0.1:57500 -delete_xpath Cisco-IOS-XR-shellutil-cfg:host-names/host-name
cisco-gnmi subscribe 127.0.0.1:57500 -debug -auto_ssl_target_override -dump_file intfcounters.proto.txt

See <rpc> --help for RPC options.


gNMI CLI demonstrating library usage.

positional arguments:
  rpc         gNMI RPC to perform against network element.

optional arguments:
  -h, --help  show this help message and exit
```

### Capabilities
This command will output the `CapabilitiesResponse` to `stdout`.
```
cisco-gnmi capabilities 127.0.0.1:57500 -auto_ssl_target_override
```

#### Usage
```
cisco-gnmi capabilities --help
usage: cisco-gnmi [-h] [-os {None,IOS XR,NX-OS,IOS XE}]
                  [-root_certificates ROOT_CERTIFICATES]
                  [-private_key PRIVATE_KEY]
                  [-certificate_chain CERTIFICATE_CHAIN]
                  [-ssl_target_override SSL_TARGET_OVERRIDE]
                  [-auto_ssl_target_override] [-debug]
                  netloc

Performs Capabilities RPC against network element.

positional arguments:
  netloc                <host>:<port>

optional arguments:
  -h, --help            show this help message and exit
  -os {None,IOS XR,NX-OS,IOS XE}
                        OS wrapper to utilize. Defaults to IOS XR.
  -root_certificates ROOT_CERTIFICATES
                        Root certificates for secure connection.
  -private_key PRIVATE_KEY
                        Private key for secure connection.
  -certificate_chain CERTIFICATE_CHAIN
                        Certificate chain for secure connection.
  -ssl_target_override SSL_TARGET_OVERRIDE
                        gRPC SSL target override option.
  -auto_ssl_target_override
                        Use root_certificates first CN as
                        grpc.ssl_target_name_override.
  -debug                Print debug messages.
```

#### Output
```
[cisco-gnmi-python] cisco-gnmi capabilities redacted:57500 -auto_ssl_target_override
Username: admin
Password:
WARNING:root:Overriding SSL option from certificate could increase MITM susceptibility!
INFO:root:supported_models {
  name: "Cisco-IOS-XR-qos-ma-oper"
  organization: "Cisco Systems, Inc."
  version: "2019-04-05"
}
...
```

### Get
This command will output the `GetResponse` to `stdout`. `-xpath` may be specified multiple times to specify multiple `Path`s for the `GetRequest`.
```
cisco-gnmi get 127.0.0.1:57500 -os "IOS XR" -xpath /interfaces/interface/state/counters -auto_ssl_target_override
```

#### Usage
```
cisco-gnmi get --help
usage: cisco-gnmi [-h] [-xpath XPATH]
                  [-encoding {JSON,BYTES,PROTO,ASCII,JSON_IETF}]
                  [-data_type {ALL,CONFIG,STATE,OPERATIONAL}] [-dump_json]
                  [-os {None,IOS XR,NX-OS,IOS XE}]
                  [-root_certificates ROOT_CERTIFICATES]
                  [-private_key PRIVATE_KEY]
                  [-certificate_chain CERTIFICATE_CHAIN]
                  [-ssl_target_override SSL_TARGET_OVERRIDE]
                  [-auto_ssl_target_override] [-debug]
                  netloc

Performs Get RPC against network element.

positional arguments:
  netloc                <host>:<port>

optional arguments:
  -h, --help            show this help message and exit
  -xpath XPATH          XPaths to Get.
  -encoding {JSON,BYTES,PROTO,ASCII,JSON_IETF}
                        gNMI Encoding.
  -data_type {ALL,CONFIG,STATE,OPERATIONAL}
                        gNMI GetRequest DataType
  -dump_json            Dump as JSON instead of textual protos.
  -os {None,IOS XR,NX-OS,IOS XE}
                        OS wrapper to utilize. Defaults to IOS XR.
  -root_certificates ROOT_CERTIFICATES
                        Root certificates for secure connection.
  -private_key PRIVATE_KEY
                        Private key for secure connection.
  -certificate_chain CERTIFICATE_CHAIN
                        Certificate chain for secure connection.
  -ssl_target_override SSL_TARGET_OVERRIDE
                        gRPC SSL target override option.
  -auto_ssl_target_override
                        Use root_certificates first CN as
                        grpc.ssl_target_name_override.
  -debug                Print debug messages.
```

#### Output
```
[cisco-gnmi-python] cisco-gnmi get redacted:57500 -os "IOS XR" -xpath /interfaces/interface/state/counters -auto_ssl_target_override
Username: admin
Password:
WARNING:root:Overriding SSL option from certificate could increase MITM susceptibility!
INFO:root:notification {
  timestamp: 1585607100869287743
  update {
    path {
      elem {
        name: "interfaces"
      }
      elem {
        name: "interface"
      }
      elem {
        name: "state"
      }
      elem {
        name: "counters"
      }
    }
    val {
      json_ietf_val: "{\"in-unicast-pkts\":\"0\",\"in-octets\":\"0\"...
```

### Set
Please note that `Set` operations may be destructive to operations and should be tested in lab conditions. Behavior is not fully validated.

#### Usage
```
cisco-gnmi set --help
usage: cisco-gnmi [-h] [-update_json_config UPDATE_JSON_CONFIG]
                  [-replace_json_config REPLACE_JSON_CONFIG]
                  [-delete_xpath DELETE_XPATH] [-no_ietf] [-dump_json]
                  [-os {None,IOS XR,NX-OS,IOS XE}]
                  [-root_certificates ROOT_CERTIFICATES]
                  [-private_key PRIVATE_KEY]
                  [-certificate_chain CERTIFICATE_CHAIN]
                  [-ssl_target_override SSL_TARGET_OVERRIDE]
                  [-auto_ssl_target_override] [-debug]
                  netloc

Performs Set RPC against network element.

positional arguments:
  netloc                <host>:<port>

optional arguments:
  -h, --help            show this help message and exit
  -update_json_config UPDATE_JSON_CONFIG
                        JSON-modeled config to apply as an update.
  -replace_json_config REPLACE_JSON_CONFIG
                        JSON-modeled config to apply as a replace.
  -delete_xpath DELETE_XPATH
                        XPaths to delete.
  -no_ietf              JSON is not IETF conformant.
  -dump_json            Dump as JSON instead of textual protos.
  -os {None,IOS XR,NX-OS,IOS XE}
                        OS wrapper to utilize. Defaults to IOS XR.
  -root_certificates ROOT_CERTIFICATES
                        Root certificates for secure connection.
  -private_key PRIVATE_KEY
                        Private key for secure connection.
  -certificate_chain CERTIFICATE_CHAIN
                        Certificate chain for secure connection.
  -ssl_target_override SSL_TARGET_OVERRIDE
                        gRPC SSL target override option.
  -auto_ssl_target_override
                        Use root_certificates first CN as
                        grpc.ssl_target_name_override.
  -debug                Print debug messages.
```

#### Output
Let's create a harmless loopback interface based from [`openconfig-interfaces.yang`](https://github.com/openconfig/public/blob/master/release/models/interfaces/openconfig-interfaces.yang).

`config.json`
```json
{
    "openconfig-interfaces:interfaces": {
        "interface": [
            {
                "name": "Loopback9339"
            }
        ]
    }
}
```

```
[cisco-gnmi-python] cisco-gnmi set redacted:57500 -os "IOS XR" -auto_ssl_target_override -update_json_config config.json
Username: admin
Password:
WARNING:root:Overriding SSL option from certificate could increase MITM susceptibility!
INFO:root:response {
  path {
    origin: "openconfig-interfaces"
    elem {
      name: "interfaces"
    }
  }
  message {
  }
  op: UPDATE
}
message {
}
timestamp: 1585715036783451369
```

And on IOS XR...a loopback interface!
```
...
interface Loopback9339
!
...
```

### Subscribe
This command will output the `SubscribeResponse` to `stdout` or `-dump_file`. `-xpath` may be specified multiple times to specify multiple `Path`s for the `GetRequest`.

```
cisco-gnmi subscribe 127.0.0.1:57500 -os "IOS XR" -xpath /interfaces/interface/state/counters -auto_ssl_target_override
```

#### Usage
```
cisco-gnmi subscribe --help
usage: cisco-gnmi [-h] [-xpath XPATH] [-interval INTERVAL]
                  [-mode {TARGET_DEFINED,ON_CHANGE,SAMPLE}]
                  [-suppress_redundant]
                  [-heartbeat_interval HEARTBEAT_INTERVAL]
                  [-dump_file DUMP_FILE] [-dump_json] [-sync_stop]
                  [-sync_start] [-encoding {JSON,BYTES,PROTO,ASCII,JSON_IETF}]
                  [-os {None,IOS XR,NX-OS,IOS XE}]
                  [-root_certificates ROOT_CERTIFICATES]
                  [-private_key PRIVATE_KEY]
                  [-certificate_chain CERTIFICATE_CHAIN]
                  [-ssl_target_override SSL_TARGET_OVERRIDE]
                  [-auto_ssl_target_override] [-debug]
                  netloc

Performs Subscribe RPC against network element.

positional arguments:
  netloc                <host>:<port>

optional arguments:
  -h, --help            show this help message and exit
  -xpath XPATH          XPath to subscribe to.
  -interval INTERVAL    Sample interval in seconds for Subscription. Defaults
                        to 10.
  -mode {TARGET_DEFINED,ON_CHANGE,SAMPLE}
                        SubscriptionMode for Subscription. Defaults to SAMPLE.
  -suppress_redundant   Suppress redundant information in Subscription.
  -heartbeat_interval HEARTBEAT_INTERVAL
                        Heartbeat interval in seconds.
  -dump_file DUMP_FILE  Filename to dump to. Defaults to stdout.
  -dump_json            Dump as JSON instead of textual protos.
  -sync_stop            Stop on sync_response.
  -sync_start           Start processing messages after sync_response.
  -encoding {JSON,BYTES,PROTO,ASCII,JSON_IETF}
                        gNMI Encoding. Defaults to whatever Client wrapper
                        prefers.
  -os {None,IOS XR,NX-OS,IOS XE}
                        OS wrapper to utilize. Defaults to IOS XR.
  -root_certificates ROOT_CERTIFICATES
                        Root certificates for secure connection.
  -private_key PRIVATE_KEY
                        Private key for secure connection.
  -certificate_chain CERTIFICATE_CHAIN
                        Certificate chain for secure connection.
  -ssl_target_override SSL_TARGET_OVERRIDE
                        gRPC SSL target override option.
  -auto_ssl_target_override
                        Use root_certificates first CN as
                        grpc.ssl_target_name_override.
  -debug                Print debug messages.
```

#### Output
```
[cisco-gnmi-python] cisco-gnmi subscribe redacted:57500 -os "IOS XR" -xpath /interfaces/interface/state/counters -auto_ssl_target_override
Username: admin
Password:
WARNING:root:Overriding SSL option from certificate could increase MITM susceptibility!
INFO:root:Dumping responses to stdout as textual proto ...
INFO:root:Subscribing to:
/interfaces/interface/state/counters
INFO:root:update {
  timestamp: 1585607768601000000
  prefix {
    origin: "openconfig"
    elem {
      name: "interfaces"
    }
    elem {
      name: "interface"
      key {
        key: "name"
        value: "Null0"
      }
    }
    elem {
      name: "state"
    }
    elem {
      name: "counters"
    }
  }
  update {
    path {
      elem {
        name: "in-octets"
      }
    }
    val {
      uint_val: 0
    }
  }
...
```

## Licensing
`cisco-gnmi-python` is licensed as [Apache License, Version 2.0](LICENSE).

## Issues
Open an issue :)

## Related Projects
1. [openconfig/gnmi](https://github.com/openconfig/gnmi)
2. [google/gnxi](https://github.com/google/gnxi)
3. [Telegraf Cisco gNMI Plugin](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/cisco_telemetry_gnmi)
