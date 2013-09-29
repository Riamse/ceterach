#!/usr/bin/python3
#-------------------------------------------------------------------------------
# This file is part of Ceterach.
# Copyright (C) 2013 Andrew Wang <andrewwang43@gmail.com>
#
# Ceterach is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# Ceterach is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Ceterach.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from ceterach import __version__

def read_long_description():
    return open("README.md").read()

required_packages = ['requests>=1.0.3', 'arrow>=0.3.5']

setup(name='ceterach',
      version=__version__,
      packages=['ceterach'],
      setup_requires=required_packages,
      install_requires=required_packages,
      url='https://github.com/Riamse/ceterach',
      license='GNU Lesser General Public License v3 or later',
      author='Andrew Wang',
      author_email='andrewwang43@gmail.com',
      description='An interface for interacting with MediaWiki',
      long_description=read_long_description(),
      keywords="ceterach wiki wikipedia mediawiki",
      classifiers=["Programming Language :: Python",
                   "Programming Language :: Python :: 3",
                   "Development Status :: 2 - Pre-Alpha",
                   "Intended Audience :: Developers",
                   ' :: '.join(["License", "OSI Approved",
                                "GNU Library or Lesser General "
                                "Public License (LGPL)"
                   ]),
                   "Operating System :: OS Independent",
                   "Topic :: Internet :: WWW/HTTP",
      ],
)
