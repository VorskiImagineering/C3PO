#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='C3PO',
    version='0.3.0',
    packages=['c3po', 'c3po.conf', 'c3po.mod', 'c3po.converters'],
    url='https://github.com/VorskiImagineering/C3PO',
    license='MIT',
    author=u'Marek Nogacki',
    author_email='m.nogacki@hiddendata.co',
    description='''C3PO is Python module responsible for converting all .po files from locale directory into one .ods
file and sending it to the Google Docs (spreadsheet link provided by user), so users with access to that spreadsheet
can translate expression included there.\n
This module provides Communicator which deals with uploading, downloading these translations and synchronizing whole
content by merging it. Package contains basic methods for converting po files into csv, ods formats and back. It also
provides methods for git push and git checkout po files into repository.''',
    install_requires=['gdata==2.0.18', 'polib==1.0.3', 'odslib==1.0.1'],
    entry_points={
        'console_scripts': [
            'c3po = c3po.c3po_cmd:main'
        ]
    },
    download_url='https://github.com/VorskiImagineering/C3PO/tarball/master',
)
