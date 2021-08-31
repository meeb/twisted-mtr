import os
import socket
import ipaddress
import random
import logging
from pathlib import Path
from .errors import SocketError
from .logger import get_logger


log = get_logger('utils', level=logging.INFO)


def find_binary(binary_name):
    '''
        Scans the $PATH for a binary by name. Returns the absolute path to
        the binary. The binary must be executable.
    '''
    log.debug(f'Scanning PATH for binary: {binary_name}')
    path_parts = os.getenv('PATH', '').split(':')
    for path_part in path_parts:
        p = Path(path_part)
        p.expanduser().resolve()
        binary_path = p / binary_name
        if os.access(binary_path, os.X_OK):
            log.debug(f'Found a binary called: '
                      f'{binary_name} at {binary_path}')
            return str(binary_path)
    log.error(f'Failed to find binary: {binary_name}')
    return False


def parse_ip(ip):
    '''
        Parses a string as either an IPv4 or IPv6 address or raises an
        exception.
    '''
    ip = str(ip).strip()
    try:
        return ipaddress.ip_address(ip)
    except (ValueError, TypeError) as e:
        raise SocketError(f'Failed to parse "{ip}" as either an IPv4 or '
                          f'IPv6 address')
