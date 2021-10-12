#!/usr/bin/env python3

'''
    An example usage for twisted-mtr which initiates multiple async traceroutes
    to multiple IPv4 and IPv6 target IP addresses at the same time. You will
    need to set your source IP addresses correctly and have a working dual
    IPv4/IPv6 networking stack to run this example.

'''

import sys
import signal
import logging
import ipaddress
from twisted.internet import reactor
from twisted_mtr import logger, errors, mtr, utils


log = logger.get_logger('trace', level=logging.DEBUG)


if __name__ == '__main__':

    log.info(f'Starting up...')

    # Find mtr-packet in your path
    mtr_binary_name = 'mtr-packet'
    mtr_binary_path = utils.find_binary(mtr_binary_name)

    # Replace with your local IPv4 address
    # Note that if you set this to an IP address not available on your system
    # your traceroutes will simply all time out
    local_ipv4 = ipaddress.IPv4Address('10.1.2.3')

    # Replace with your local IPv6 address
    # Note that if you set this to an IP address not available on your system
    # your traceroutes will simply all time out
    local_ipv6 = ipaddress.IPv6Address('2404:1:2:3:4:5:6:7')

    # Create the TraceRoute Twisted process object
    app_mtr = mtr.TraceRoute(
        mtr_binary_path=mtr_binary_path,
        local_ipv4=local_ipv4,
        local_ipv6=local_ipv6
    )

    # Bind to the Twisted tractor with the mtr-packet binary
    reactor.spawnProcess(app_mtr, mtr_binary_name, [mtr_binary_path], {})

    # Sets to track the traceroutes that have been dispatched and completed
    requested = set()
    completed = set()

    # Success callback
    def _test_traceroute_callback(target_ip, protocol, port, hops):
        log.info(f'Completed traceroute to: {target_ip} ({protocol}:{port})')
        completed.add(str(target_ip))
        for (hop_num, hop_ip, microseconds) in hops:
            log.info(f' - {hop_num} {hop_ip} {microseconds}')
        if requested == completed:
            log.info('All traces complete, stopping reactor')
            reactor.stop()

    # Error callback
    def _test_trace_error(counter, joined_request, error, extra):
        log.error(f'Error running traceroute: {error}')
        reactor.stop()

    # Queue up our traceroutes
    target_ip = utils.parse_ip('8.1.1.1')  # No route after a few hops to test
    requested.add(str(target_ip))
    app_mtr.trace(_test_traceroute_callback, _test_trace_error, target_ip)
    target_ip = utils.parse_ip('8.8.8.8')
    requested.add(str(target_ip))
    app_mtr.trace(_test_traceroute_callback, _test_trace_error, target_ip)
    target_ip = utils.parse_ip('1.1.1.1')
    requested.add(str(target_ip))
    app_mtr.trace(_test_traceroute_callback, _test_trace_error, target_ip,
                  protocol='tcp', port=53)
    target_ip = utils.parse_ip('2404:6800:4015:802::200e')
    requested.add(str(target_ip))
    app_mtr.trace(_test_traceroute_callback, _test_trace_error, target_ip)
    target_ip = utils.parse_ip('2606:4700::6810:7b60')
    requested.add(str(target_ip))
    app_mtr.trace(_test_traceroute_callback, _test_trace_error, target_ip)

    # Polite hook for control+c to abort the traceroutes before they complete
    def signal_handler(sig, frame):
        sys.stdout.write('\n')  # put the ^C on its own line
        log.info(f'Caught keyboard interrupt, shutting down...')
        reactor.stop()

    signal.signal(signal.SIGINT, signal_handler)

    # Start the Twisted reactor event loop
    log.info(f'Starting event loop...')
    reactor.run()

    # If we reach here the reactor has been stopped, all done
    log.info(f'Goodbye')
