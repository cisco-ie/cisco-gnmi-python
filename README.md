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

### Client
`Client` is a very barebones class simply implementing `capabilities`, `get`, `set`, and `subscribe` methods. It provides some context around the expectation for what should be supplied to these RPC functions and helpers for validation.

Methods are documented in [`src/cisco_gnmi/client.py`](src/cisco_gnmi/client.py).

#### Initialization
Since `v0.1.1` the `Client` initialization has changed to a builder pattern which initializes the object but relies on method chaining for declaring how to behave. This section covers some of the potential usage of the `Client` and any wrapper classes derived from `Client`.

The inheritance is scoped as `Base -> Client -> Wrapper`. `Base` contains the core gRPC functionality, `Client` implements the gNMI RPCs and common functionality, and `Wrapper` classes provide OS-specific constraints and functionality. `Base` is really the core of this initialization section, but `Client`-derived classes are user-facing thus deserving the documentation.

There are four major methods involved here: `__init__`, `as_secure`, `as_insecure`, and `with_authentication`.

```python
__init__(
    self,
    target,
    timeout=Base._C_MAX_LONG
    attempt_implicit_secure=False
)
```

* `target` is the hostname/IP and port of the network element to interact with, e.g. `127.0.0.1:9339`.
* `timeout` is the amount of time in seconds to await before timing out per RPC.
* `attempt_implicit_secure` indicates whether to attempt to immediately connect to the network element, acquire whatever certificate is available, and set up an encrypted channel utilizing the retrieved certificate. This is still insecure, but encrypted and useful for testing TLS functionality.

```
as_secure(
    self,
    root_certificates=None,
    private_key=None,
    certificate_chain=None,
    root_from_target=False,
    target_name_from_root=False,
    channel_options=None,
    from_file=False
)
```

* `root_certificates`, `private_key`, and `certificate_chain` all simply just wrap [`grpc.ssl_channel_credentials`](https://grpc.github.io/grpc/python/grpc.html#grpc.ssl_channel_credentials) and correspond directly.
* `root_from_target` indicates to download the root certificate from the target network element.
* `target_name_from_root` attempts to extract the `grpc.ssl_target_name_override` option with the first CN attribute in the root certificate. This effectively allows us to skip the server name verification of the certificate. This functionality mimics a subset of Go's `TLS.InsecureSkipVerify` which leaves TLS susceptible to MITM attacks - only use for testing.
* `channel_options` is an array of gRPC option tuples, such as `[("grpc.ssl_target_name_override", "ems.cisco.com")]`. This assumes some knowledge of gRPC options.
* `from_file` indicates that the `root_certificates`, `private_key`, and `certificate_chain` variables represent file paths which should be read from the filesystem as opposed to the certificate content being passed directly in the variables.

```python
as_insecure(
    self,
    channel_options=None,
    compression=None
)
```

* `as_insecure` utilizes an insecure gRPC channel and is explicitly against gNMI specification. This option is not recommended and exists purely due to insecure server implementations existing. Utilizing `as_secure(root_from_target=True, target_name_from_root=True)` should negate most necessity or desire for this option.

```python
with_authentication(
    self,
    username,
    password
)
```

* This method simply sets the `username` and `password` to utilize for authenticating RPCs with the devices as metadata (Call credentials).

#### Initialization Examples

Using an encrypted channel automatically getting the certificate from the device, quick for testing:

```python
from cisco_gnmi import Client

client = Client(
    '127.0.0.1:9339',
    attempt_implicit_secure=True
).with_authentication(
    'admin',
    'its_a_secret'
)

# More explicitly...

client = Client(
    '127.0.0.1:9339'
).as_secure(
    root_from_target=True,
    target_name_from_root=True
).with_authentication(
    'admin',
    'its_a_secret'
)
```


Using an owned root certificate on the filesystem:
```python
from cisco_gnmi import Client

client = Client(
    '127.0.0.1:9339'
).as_secure(
    'ems.pem',
    from_file=True
).with_authentication(
    'admin',
    'its_a_secret'
)
```

Passing certificate content to method:

```python
from cisco_gnmi import Client

# Note reading as bytes
with open('ems.pem', 'rb') as cert_fd:
    root_cert = cert_fd.read()

client = Client(
    '127.0.0.1:9339'
).as_secure(
    root_cert
).with_authentication(
    'admin',
    'its_a_secret'
)
```

Usage with root certificate, private key, and cert chain:

```python
from cisco_gnmi import Client

client = Client(
    '127.0.0.1:9339'
).as_secure(
    root_certificates='rootCA.pem',
    private_key='client.key',
    certificate_chain='client.crt',
    from_file=True
).with_authentication(
    'admin',
    'its_a_secret'
)
```


### XRClient
`XRClient` inherets from `Client` and provides several wrapper methods which aid with IOS XR-specific behaviors of the gNMI implementation. These are `delete_xpaths`, `get_xpaths`, `set_json`, and `subscribe_xpaths`. These methods make several assumptions about what kind of information will be supplied to them in order to simplify usage of the gNMI RPCs.

Methods are documented in [`src/cisco_gnmi/xr.py`](src/cisco_gnmi/xr.py).

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
# Now use pipenv
pipenv --three install --dev
# Enter virtual environment
pipenv shell
# Do your thing.
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
