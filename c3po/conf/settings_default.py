#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))

# List of languages to read from and write po file to
LANGUAGES = ['en', 'pl', 'jp']

# GDocs authentication information
EMAIL = 'ttestt123321@gmail.com'
PASSWORD = 'zxcasdqwe.'
URL = 'https://docs.google.com/spreadsheet/ccc?key=0AnVOHClWGpLZdFdNVVJJLUZkbkh1bGFOWUZqRnYxbGc#gid=0'

# Header which will be attached on top of every po file
HEADER = '# translated with c3po\n'

# Path to locale folder with language directories
LOCALE_ROOT = os.path.join(ROOT_DIR, 'conf', 'locale')
# Path from lang folder to po file
PO_FILES_PATH = 'LC_MESSAGES'
# Temporary directory where csv file and temp lines.txt will be saved
TEMP_PATH = os.path.join(ROOT_DIR, 'temp')

# Git information
GIT_REPOSITORY = 'git@git.hiddendata.co:mnogacki/testpo.git'
GIT_BRANCH = 'master'
GIT_MESSAGE = 'Message'

# Source to identify user later on GDocs
SOURCE = 'PO Translator'

METADATA = {
    'MIME-Version': '1.0',
    'Content-Type': 'text/plain; charset=UTF-8',
    'Content-Transfer-Encoding': '8bit',
}
