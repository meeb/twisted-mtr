import logging
from time import time
from twisted.internet import reactor, protocol
from .logger import get_logger
from .errors import MTRError


log = get_logger('mtr', level=logging.INFO)


class TraceRoute(protocol.ProcessProtocol):

    REQUEST_TIMEOUT = 5   # Seconds, passed to mtr-packet
    WAIT_TIMEOUT = 7      # Seconds, less than the 10 second timeout MTR uses
    RETRY_WAIT = 3        # Seconds, time to wait before retrying requests
    MAX_TTL = 50          # Maximum TTL, this also sets as max route hops
    NO_REPLY_MAX_TTL = 10 # Maximum number of hops to try after a no-reply
    # NOTE: WAIT_TIMEOUT must be greater than REQUEST_TIMEOUT
    # NOTE: (REQUEST_TIMEOUT * NO_REPLY_MAX_TTL) should be LESS than 60

    def __init__(self, mtr_binary_path=None, local_ipv4=None, local_ipv6=None):
        self.request_counter = 0
        self.requests = {}
        self.mtr_binary_path = mtr_binary_path
        self.local_ipv4 = local_ipv4
        self.local_ipv6 = local_ipv6
        if not self.local_ipv4 and not self.local_ipv6:
            raise MTRError('At least one of local_ipv4 or local_ipv6 '
                           'must be set, preferably both if available')

    def reset(self):
        self.request_counter = 0
        self.requests = {}

    def inc_counter(self):
        self.request_counter += 1
        # mtr counters are stored as a signed long, so wrap if they're too high
        if self.request_counter > 2147483647:
            if 0 in self.requests:
                # We're wrapping to 0 from 2147483647 but a request is still
                # outstanding from 0, something has gone very wrong somewhere
                raise MTRError(f'Wrapped MTR request counter to 0 but a '
                               f'request with id 0 is still outstanding. '
                               f'This is a bug, please report it.')
            self.request_counter = 0

    def connectionMade(self, *a, **k):
        self.reset()
        log.debug(f'Connected to subprocess of: {self.mtr_binary_path}')

    def outReceived(self, data):
        self.got_mtr_line(data.decode().split())

    def errReceived(self, data):
        log.error(f'Recieved error from process: {data}')

    def inConnectionLost(self):
        log.debug(f'Connection from client lost')

    def outConnectionLost(self):
        log.debug(f'Connection to child process lost')

    def errConnectionLost(self):
        log.debug(f'Child process closed their stderr')

    def processExited(self, reason):
        log.debug(f'Child process exited, reason: {reason}')

    def processEnded(self, reason):
        log.debug(f'Child processed ended, reason: {reason}')

    def send_mtr_line(self, line=[]):
        log.debug(f'Writing MTR command: {line}')
        self.transport.write(' '.join(line).encode() + b'\n')

    def got_mtr_line(self, line=[]):
        '''
            Called when a line is recieved from MTR. The first part of the line
            is the request counter. If the counter is for an expected request
            cancel the timeout check and call the requests callback, otherwise
            log the line as an unexpected response
        '''
        if len(line) == 0:
            log.error('Recieved MTR response with no content')
        try:
            c = int(line[0])
        except (ValueError, TypeError) as e:
            log.error(f'Failed to parse first part of MTR reponse as a '
                      f'counter: {line} ({e})')
            return
        if c not in self.requests:
            log.error(f'Recieved MTR response for an unknown request: {line}')
            return
        callback, errback, timeout_check, request, extra = self.requests[c]
        del self.requests[c]
        timeout_check.cancel()
        log.debug(f'{len(self.requests)} requests expected')
        joined_request = ' '.join(request[1:])
        joined_response = ' '.join(line[1:])
        log.debug(f'Recieved MTR response for "{c} {joined_request}" '
                  f'-> "{c} {joined_response}"')
        callback(c, request, line[1:], extra)

    def check_timeout(self, c):
        '''
            Fired after TIMEOUT seconds to verify a response has been recieved
            for an MTR request. If a response has not been recieved log it and
            cancel the request.
        '''
        if c not in self.requests:
            log.error(f'Timeout check fired for a request which no '
                      f'longer exists: {c}')
            return
        callback, errback, timeout_check, request, extra = self.requests[c]
        del self.requests[c]
        joined_request = ' '.join(request[1:])
        log.debug(f'MTR request "{c} {joined_request}" timed out '
                  f'after {self.WAIT_TIMEOUT} seconds')
        errback(c, request, 'timeout', extra)

    def mtr_request(self, callback, errback, request, extra):
        '''
            Makes a a request to MTR. This writes the line to the stdin of the
            mtr-packet process with a counter for the line, then waits to see
            if a response line is received within the timeout window. "extra"
            is an arbitrary value to pass on to the callbacks if additional
            state information is required.
        '''
        joined_request = ' '.join(request)
        c = self.request_counter
        self.inc_counter()
        self.requests[c] = (
            callback,
            errback,
            reactor.callLater(self.WAIT_TIMEOUT, self.check_timeout, c),
            request,
            extra
        )
        line = f'{c} {joined_request}\n'
        log.debug(f'Sending MTR request "{line.strip()}"')
        self.transport.write(line.encode())

    def trace(self, callback, errback, ip_address, extra=None):
        '''
            A higher level method that chains send-probe requests with
            increasing TTLs until an error is recieved or the responding IP is
            that of the target IP. Note that unlike lower level methods
            ip_address here is an IPAddress object not a string.
        '''
        hops = []
        ttl = 1
        if ip_address.version == 4:
            if not self.local_ipv4:
                raise MTRError('Trace to an IPv4 address was requested but '
                               'no local IPv4 origin has been specified. Set '
                               'the local_ipv4 argument.')
            local_family = 'local-ip-4'
            local_ip = str(self.local_ipv4)
            target_family = 'ip-4'
        else:
            if not self.local_ipv6:
                raise MTRError('Trace to an IPv6 address was requested but '
                               'no local IPv6 origin has been specified. Set '
                               'the local_ipv6 argument.')
            local_family = 'local-ip-6'
            local_ip = str(self.local_ipv6)
            target_family = 'ip-6'

        def _got_reply(c, request, line, extra):
            # Callback for a single request response
            hop_num, no_reply_hops = extra
            send_next = False
            trace_complete = False
            ttl = None
            if not line:
                _got_error(c, request, 'no response line', extra)
                return
            response_type = line[0]
            if response_type == 'ttl-expired':
                # Not reached the end of the trace yet, expiry notice from hop:
                #   ttl-expired ip-4 10.0.0.1 round-trip-time 400
                hops.append((hop_num, line[2], int(line[4])))
                # Flag to trace to the next hop as we're not done
                send_next = True
                ttl = int(request[-1])
            elif response_type == 'reply':
                # Reached the end of the trace, reply from the target IP
                #   reply ip-4 1.2.3.4 round-trip-time 254144
                hops.append((hop_num, line[2], int(line[4])))
                # Mark the trace as complete
                trace_complete = True
            elif response_type == 'no-reply':
                # No reply from IP
                #    no-reply
                hops.append((hop_num, None, None))
                no_reply_hops += 1
                # Check if we should try additional hops
                if no_reply_hops >= self.NO_REPLY_MAX_TTL:
                    # We've already tried a additional hops, we're done
                    trace_complete = True
                else:
                    # Try the next hop
                    send_next = True
                    ttl = int(request[-1])
            elif response_type == 'no-route':
                # There was no route to the host used in a send-probe request
                _got_error(c, request,
                           (f'failed to send-probe to {ip_address}: no '
                            f'route to host'),
                           extra)
                return
            elif response_type == 'network-down':
                # A probe could not be sent because the network is down
                _got_error(c, request,
                           (f'failed to send-probe to {ip_address}: '
                            f'network is down'),
                           extra)
                return
            elif response_type == 'probes-exhausted':
                # A probe could not be sent because there are already too many
                # unresolved probes already in flight
                log.error(f'Failed to send probe to {ip_address} with TTL '
                          f'{ttl}: too many probes in flight, will retry in '
                          f'{self.RETRY_WAIT} seconds...')
                reactor.callLater(self.RETRY_WAIT, trace_to_hop,
                                  str(ip_address), ttl, extra)
                return
            elif response_type == 'permission-denied':
                # The operating system denied permission to send the probe with
                # the specified options
                _got_error(c, request,
                           (f'failed to send-probe to {ip_address}: '
                            f'permission denied'),
                           extra)
                return
            else:
                # Unknown reply
                _got_error(c, request,
                           f'unknown response type: {response_type}',
                           extra)
                return
            if trace_complete:
                # We're all done, fire the upstream callback
                hops_log = ' '.join(f'{hop}|{ip},{ms}' for hop, ip, ms in hops)
                log.debug(f'Completed trace to {ip_address}: {hops_log}')
                callback(ip_address, hops)
            elif send_next:
                # Send the request to the next hop
                trace_to_hop(
                    str(ip_address),
                    ttl + 1,
                    (hop_num + 1, no_reply_hops)
                )

        def _got_error(c, request, error, extra):
            # Error callback for a single request response
            if error == 'timeout':
                # mtr-packet didn't reply in time, retry it
                target_ip = request[4]
                ttl = request[8]
                log.error(f'Probe to {target_ip} with TTL {ttl} had no reply '
                          f'from mtr, retrying...')
                reactor.callLater(self.RETRY_WAIT, trace_to_hop,
                                  target_ip, ttl, extra)
                #trace_to_hop(target_ip, ttl, extra)
            else:
                # Something else went wrong, send it to the upstream errback()
                errback(c, request, error, extra)

        def trace_to_hop(target_ip, ttl, extra):
            # Make a single send-probe request
            request = [
                'send-probe',
                local_family, local_ip,
                target_family, target_ip,
                'timeout', str(self.REQUEST_TIMEOUT),
                'ttl', str(ttl)
            ]
            self.mtr_request(_got_reply, _got_error, request, extra)

        # Start the trace off, (hop_num, no_reply_hops) stored in "extra"
        log.debug(f'Starting trace to: {ip_address}')
        ttl, hop_num, no_reply_hops = 1, 1, 0
        trace_to_hop(str(ip_address), ttl, (hop_num, no_reply_hops))
