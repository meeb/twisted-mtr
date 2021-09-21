import os
import sys
from setuptools import setup, find_packages


version = '1.0.1'


with open('README.md', 'rt') as f:
    long_description = f.read()


with open('requirements.txt', 'rt') as f:
    requirements = tuple(f.read().split())


setup(
    name = 'twisted_mtr',
    version = version,
    url = 'https://github.com/meeb/twisted-mtr',
    author = 'https://github.com/meeb',
    author_email = 'meeb@meeb.org',
    description = ('Python Twisted library that performs high performance'
                   'asynchronous traceroutes using mtr-packet.'),
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    license = 'BSD',
    include_package_data = True,
    install_requires = requirements,
    packages = find_packages(),
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords = ('mtr', 'twisted', 'traceroute', 'async', 'asynchronous',
                'trace', 'tracert', 'tx')
)
