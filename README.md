# twisted-mtr

A Python Twisted library that performs asynchronous high performance
traceroutes using mtr-packet.

`twisted-mtr` is designed to enable Twisted (as in the
[Python Twisted networking framework](https://twistedmatrix.com/) to perform
fully asynchronous IPv4 and IPv6 traceroutes.


## Installation

`twisted-mtr` requires the Twisted library as a dependancy as well as the the
`mtr-packet` binary to be available in your systems PATH. You can install
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
examples. There may not be a suitable option for Windows systems and Windows
support has not been tested.

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
from twisted.internet import reactor 
from twisted_mtr import utils, mtr

# Find mtr-packet
mtr_binary_name = 'mtr-packet'
mtr_binary_path = utils.find_binary(mtr_binary_name)

# Replace with a local IPv4 address
local_ipv4 = ipaddress.IPv4Address('10.11.22.33')

# Address we're tracing to
target_ipv4 = ipaddress.IPv4Address('1.1.1.1')

# Create the Twisted Protocol instance
app_mtr = mtr.TraceRoute(mtr_binary_path=mtr_binary_path,
                         local_ipv4=local_ipv4)

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


# API synopsis

`twisted-mtr` has really only one class you would interact with at
`twisted_mtr.mtr.TraceRoute` that takes the following parameters:

```python
my_traceroute_object = TraceRoute(
    # Full path to your mtr-packet binary
    mtr_binary_path='/usr/bin/mtr-packet',
    # An IPv4Address object for your local (source) IPv4 address
    local_ipv4=ipaddress.IPv4Adddress('127.2.3.4'),
    # An IPv6Address object for your local (source) IPv6 address
    local_ipv6=ipaddress.IPv6Adddress('::1')
)
```

You may leave `local_ipv4` or `local_ipv6` out if your system only has IPv4
or IPv6 available, however at least one of them must be set or an exception
will be raised.

You can, for obvious reasons, only send IPv4 traceroutes if `local_ipv4` is
set and you can only send IPv6 traceroutes if `local_ipv6` is set.

If you set your `local_ipv*` address incorrectly your traceroutes may trigger
the error callback with a network error or simply time out.

Once your `TraceRoute` object has been created you start a traceroute with
the following method:

```python
my_traceroute_object.trace(
    # Must be a function that exists or a lambda
    success_callback_function,
    # Must be a function that exists or a lambda
    failure_callback_function,
    # An IPv4Address or IPv6Address object of the address to traceroute to
    ipaddress.IPv4Address('1.1.1.1'),
    # The protocol to use, defaults to 'icmp', can be 'icmp' or 'tcp'
    protocol='icmp',
    # The port number to use if the protocol is 'tcp', otherwise ignored
    port=None
)
```

When the traceroute completes or errors the callbacks will be called with the
following parameters:

```python
def success_callback_function(target_ip, hops):
    # target_ip is an IPvNAddress object of the address the traceroute was to
    print(f'Completed trace to: {target_ip}')
    # hops is a list of the traceroute hops, each hop has 5 parameters, e.g.
    #hops = [
    #    (1, '10.0.0.1', 20, 'icmp', None),
    #    (2, '22.22.22.22', 111, 'icmp', None),
    #    (3, '33.33.33.33', 222, 'icmp', None),
    #    (4,  None, None, 'icmp', None),
    #    (5, '55.55.55.55', 444, 'icmp', None),
    #]
    # The IP and milliseconds of the hop may be None if the hop did not
    # respond to the traceroute request or it timed out. Parameter 4 is the
    # protocol of the trace. Prameter 5 is the port number if the protocol is
    # 'tcp'. Example TCP trace hop:
    #  (1, '10.0.0.1', 20, 'tcp', 443)
    for hop in hops:
        hop_number, hop_ip, latency_in_milliseconds, protocol, port = hop
        print(f' - {hop}: {hop_ip} {latency_in_milliseconds} ms '
              f'({protocol}:{port})')

def failure_callback_function(hop_number, request, error, extra):
    # Errors are things like mtr-packet return a serious error for your
    # traceroute request or network errors, not Python errors.
    #
    # hop_number is the traceroute hop where the error occured
    # request the mtr-packet request that generated the error
    # error is the error message as a string
    # extra is any addtional data that was bundled with the request
    print(f'An error occured at hop {hop_number} sending MTR request '
          f'"{request}" with error: {error}')
```


# Tests

There is a test suite that you can run by cloning this repository, installing
the required dependancies and execuiting:

```bash
$ make test
```


# Debugging

`twisted-mtr` will emit debug logs if you use Python's logging module. Enable
them with `level=logging.DEBUG` in your application when you initialise your
logger.


# Contributing

All properly formatted and sensible pull requests, issues and comments are
welcome.
