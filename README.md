# cisco-gnmi-python
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

This library wraps gNMI functionality to ease usage with Cisco implementations in Python programs. Derived from [openconfig/gnmi](https://github.com/openconfig/gnmi/tree/master/proto).

## Usage
```bash
pip install cisco-gnmi
python -c "import cisco_gnmi; print(cisco_gnmi)"
```

This library covers the gNMI defined `capabilities`, `get`, `set`, and `subscribe` RPCs, and helper clients provide OS-specific recommendations. As commonalities and differences are identified this library will be refactored as necessary.

It is *highly* recommended that users of the library learn [Google Protocol Buffers](https://developers.google.com/protocol-buffers/) syntax to significantly ease usage. Understanding how to read Protocol Buffers, and reference [`gnmi.proto`](https://github.com/openconfig/gnmi/blob/master/proto/gnmi/gnmi.proto), will be immensely useful for utilizing gNMI and any other gRPC interface.

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

## Licensing
`cisco-gnmi-python` is licensed as [Apache License, Version 2.0](LICENSE).

## Issues
Open an issue :)

## Related Projects
1. [openconfig/gnmi](https://github.com/openconfig/gnmi)
2. [google/gnxi](https://github.com/google/gnxi)
3. [Telegraf Cisco gNMI Plugin](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/cisco_telemetry_gnmi)
