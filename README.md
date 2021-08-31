# twisted-mtr

A Python Twisted library that performs asynchronous high performance
traceroutes using mtr-packet.

`twisted-mtr` is designed to enable Twisted (as in the
[Python Twisted networking framework](https://twistedmatrix.com/) to perform
fully asynchronous IPv4 and IPv6 traceroutes.


## Installation

`twisted-mtr` requires the Twisted library as a dependancy as well as the the
mtr-packet` binary to be available in your systems PATH. You can install
`twisted-mtr` via pip:

```bash
$ pip install twisted-mtr
```

Any modern version of Python3 will be compatible.

For `mtr-packet` this is typically available from your systems package manager.
For example on Debian / Ubuntu based systems install the `mtr-tiny` package:

```bash
# Will need to be run as root
$ apt install mtr-tiny
```

For Fedora / Redhat based systems this package is called `mtr`:

```bash
# Will need to be run as root
$ yum install mtr
```

For Alpine based systems this package is called `mtr`:

```bash
# Will need to be run as root
$ apk add mtr
```

Consult whatever package manager your system uses if it's not one of the above
examples. There may not be a suitable option for Windows systems.

Once you have Python, Twisted, the `twisted-mtr` library and the `mtr-packet`
binary installed you are good to go.


## Usage

`twisted-mtr` requires a source IP, either IPv4 or IPv6, as the source of your
traceroutes. This is not detected for you and needs to be manually set. It's
outside the scope of this library to detect your local IP. Specifying the IP
address also selects which physical or virtual network interface you want to
send the traceroutes from.

A helper utility exists to help find the path to your `mtr-packet` binary.

A basic example would be:

```python
import ipaddress
from twisted_mtr import utils, mtr

# Find mtr-packet
mtr_binary_name = 'mtr-packet'
mtr_binary_path = utils.find_binary(mtr_binary_name)

# Replace with a local IPv4 address
local_ipv4 = ipaddress.IPv4Address('10.11.22.33')

# Address we're tracing to
target_ipv4 = ipaddress.IPv4Address('1.1.1.1')

# Create the Twisted Protocol instance
app_mtr = mtr.TraceRoute(mtr_binary_path=mtr_binary_path,local_ipv4=local_ipv4)

# Spawn the mtr-packet process attached to the protocol
reactor.spawnProcess(app_mtr, mtr_binary_name, [mtr_binary_path], {})

# Callback fired when the traceroute is complete
def traceroute_complete(target_ip, hops):
    print(f'Traceroute complete to {target_ip} in {len(hops)} hops')
    for (hop_num, hop_ip, microseconds) in hops:
        print(f' - {hop_num} {hop_ip} {microseconds}')
    # Trace complete, stop the reactor
    reactor.stop()

# Callback fired if there's an error
def trace_error(counter, joined_request, error, extra):
    print(f'Error running traceroute: {error}')
    # Error during traceroute, stop the reactor
    reactor.stop()

# Start our trace with our callbacks set
app_mtr.trace(traceroute_complete, trace_error, target_ip)

# Start the Twisted reactor to begin the traceroute
reactor.run()
```

See [example-trace.py](example-trace.py) for an example implementation with
multiple IPv4 and IPv6 traceroutes running concurrently.


# Tests

There is a test suite that you can run by cloning this repository, installing
the required dependancies and execuiting:

```bash
$ make test
```


# Contributing

All properly formatted and sensible pull requests, issues and comments are
welcome.
