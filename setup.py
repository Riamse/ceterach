#!/usr/bin/python3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from ceterach import __version__

def read_long_description():
    with open("README") as f:
        text = f.read()
    return text

setup(
    name='ceterach',
    version=__version__,
    packages=['ceterach'],
#    requires=['beautifulsoup4 >= 4.1.3',
#              'requests >= 0.14.1',
#    ],
    url='https://github.com/Riamse/ceterach',
    license='GNU Lesser General Public License v2.1 or later',
    author='Andrew Wang',
    author_email='andrewwang43@gmail.com',
    description='An interface for interacting with MediaWiki',
    keywords="ceterach wiki wikipedia mediawiki",
    classifiers=("Programming Language :: Python",
                 "Programming Language :: Python :: 3",
                 "Development Status :: 2 - Pre-Alpha",
                 "Intended Audience :: Developers",
                 ' :: '.join(["License", "OSI Approved",
                              "GNU Library or Lesser General "
                              "Public License (LGPL)"
                 ]),
                 "Operating System :: OS Independent",
                 "Topic :: Internet :: WWW/HTTP",
    ),
)
