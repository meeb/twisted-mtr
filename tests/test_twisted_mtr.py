import os
import sys
import ipaddress
import unittest
from twisted.internet import reactor
from twisted_mtr import errors, mtr, utils


class TwstedMTRTestCase(unittest.TestCase):

    maxDiff = None

    def test_utils_find_binary(self):
        # Try to find the binary for test runner Python executable
        executable_path = sys.executable
        executable_name = os.path.basename(executable_path)
        detected_path = utils.find_binary(executable_name)
        self.assertEqual(executable_path, detected_path)

    def test_utils_parse_ip(self):
        with self.assertRaises(errors.SocketError):
            utils.parse_ip('')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip('.....')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip(b'test')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip('1.1.1.1.1')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip(':::')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip('1:1:1:1:1:')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip('127.0.0.1/32')
        with self.assertRaises(errors.SocketError):
            utils.parse_ip('::1/128')
        self.assertEqual(
            ipaddress.IPv4Address('127.0.0.1'),
            utils.parse_ip('127.0.0.1')
        )
        self.assertEqual(
            ipaddress.IPv4Address('8.8.8.8'),
            utils.parse_ip('8.8.8.8')
        )
        self.assertEqual(
            ipaddress.IPv6Address('2404:6800:4015:802::200e'),
            utils.parse_ip('2404:6800:4015:802::200e')
        )

    def test_traceroute(self):

        done = {4: False, 6: True}

        def _check_tests_done():
            if done[4] and done[6]:
                reactor.stop()

        # IPv4
        mtr_binary_name = 'mtr-packet'
        mtr_binary_path = utils.find_binary(mtr_binary_name)
        local_ipv4 = ipaddress.IPv4Address('127.0.0.1')
        app_mtr = mtr.TraceRoute(
            mtr_binary_path=mtr_binary_path,
            local_ipv4=local_ipv4,
            local_ipv6=None
        )
        reactor.spawnProcess(app_mtr, mtr_binary_name, [mtr_binary_path], {})

        def _test_ipv4_callback(target_ip, hops):
            self.assertEqual(target_ip, ipaddress.IPv4Address('127.0.0.1'))
            self.assertEqual(len(hops), 1)
            hop = hops[0]
            counter, hop_ip, ms = hop
            self.assertEqual(counter, 1)
            self.assertEqual(hop_ip, '127.0.0.1')
            self.assertIsInstance(ms, int)
            done[4] = True
            _check_tests_done()

        def _test_ipv4_error(counter, joined_request, error, extra):
            done[4] = True
            _check_tests_done()
        
        target_ip = utils.parse_ip('127.0.0.1')
        app_mtr.trace(_test_ipv4_callback, _test_ipv4_error, target_ip)

        # IPv6
        mtr_binary_name = 'mtr-packet'
        mtr_binary_path = utils.find_binary(mtr_binary_name)
        local_ipv6 = ipaddress.IPv6Address('::1')
        app_mtr = mtr.TraceRoute(
            mtr_binary_path=mtr_binary_path,
            local_ipv4=None,
            local_ipv6=local_ipv6
        )
        reactor.spawnProcess(app_mtr, mtr_binary_name, [mtr_binary_path], {})

        def _test_ipv6_callback(target_ip, hops):
            self.assertEqual(target_ip, ipaddress.IPv6Address('::1'))
            self.assertEqual(len(hops), 1)
            hop = hops[0]
            counter, hop_ip, ms = hop
            self.assertEqual(counter, 1)
            self.assertEqual(hop_ip, '::1')
            self.assertIsInstance(ms, int)
            done[6] = True
            _check_tests_done()

        def _test_ipv6_error(counter, joined_request, error, extra):
            done[6] = True
            _check_tests_done()
        
        target_ip = utils.parse_ip('::1')
        app_mtr.trace(_test_ipv6_callback, _test_ipv6_error, target_ip)

        # Start reactor to initiate the tests
        reactor.run()
