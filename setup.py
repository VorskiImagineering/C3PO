#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='C3PO',
    version='0.0.1',
    packages=['c3po', 'c3po.conf', 'c3po.mod'],
    url='http://www.hiddendata.co/',
    license='MIT',
    author=u'Marek Nogacki',
    author_email='m.nogacki@hiddendata.co',
    description='Upload/download po files to GDocs',
    install_requires=['gdata==2.0.18', 'polib==1.0.3', 'odslib==1.0.1'],
    entry_points={
        'console_scripts': [
            'c3po = c3po.c3po_cmd:main'
        ]
    },
)
