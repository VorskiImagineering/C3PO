#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import os
import shutil
import sys

from c3po.conf import settings


ALLOWED_COMMANDS = ('synchronize', 'download', 'upload', 'clear', 'checkout', 'push')


def usage():
    print('Usage: ./c3po.py <command> <options>\n\n'
          'Commands are:\n'
          'synchronize\tdownloads GDocs and synchronizes it\'s content with local po files\n'
          'download\tdownloads GDoc and converts it to po files\n'
          'upload\t\tuploads local po files to GDocs overwriting it\n'
          'clear\t\tclears GDoc file\n'
          'push\t\tpush project into git repository\n'
          'checkout\tcheckout git project\n\n'
          'Options are:\n'
          '-e <email>, --email=<email>\tGoogle Docs email address\n'
          '-p <pass>, --password=<pass>\tGoogle Docs password\n'
          '-u <url>, --url=<url>\t\tSpreadsheet URL\n'
          '-l <dir>, --locale=<dir>\tLocale directory path\n'
          '-P <dir>, --po-path=<dir>\tPath from concrete lang dir to .po file\n'
          '-m <msg>, --message=<msg>\tSpecify git message\n'
          '-h, --help\t\t\tShow this help message\n')


def _get_command(params_command):
    if params_command in ALLOWED_COMMANDS:
        command = params_command
    else:
        usage()
        sys.exit()
    return command


def _get_params_from_options(opts):
    params = {}
    for option, param in opts:
        if option in ('-h', '--help'):
            usage()
            sys.exit()
        elif option in ('-e', '--email'):
            params['EMAIL'] = param
        elif option in ('-p', '--password'):
            params['PASSWORD'] = param
        elif option in ('-u', '--url'):
            params['URL'] = param
        elif option in ('-l', '--locale'):
            params['LOCALE_ROOT'] = param
        elif option in ('-P', '--po-path'):
            params['PO_FILES_PATH'] = param
        elif option in ('-s', '--settings'):
            params['SETTINGS'] = param
        elif option in ('-m', '--message'):
            params['GIT_MESSAGE'] = param
        else:
            usage()
            sys.exit()
    return params


def _set_settings_file(settings, params):
    if 'SETTINGS' in params:
        settings.set_config(params['SETTINGS'], params)
    else:
        user_settings_path = os.path.expanduser('~/.c3po/settings.py')
        if os.path.exists(user_settings_path):
            settings.set_config(user_settings_path, params)
        else:
            if not os.path.isdir(os.path.dirname(user_settings_path)):
                os.makedirs(os.path.dirname(user_settings_path))
            shutil.copy(os.path.join(os.path.dirname(__file__), '..', 'conf', 'settings_default.py'),
                        user_settings_path)
            settings.set_config(user_settings_path, params)

    return settings


def initialize():
    """
    Function to initialize settings from command line and/or custom settings file
    :return: Returns str with operation type
    """
    if len(sys.argv) == 1:
        usage()
        sys.exit()

    command = _get_command(sys.argv[1])

    try:
        opts, args = getopt.getopt(sys.argv[2:], 'h:e:p:u:l:P:s:m:',
                                   ['help', 'email=', 'password=', 'url=', 'locale=',
                                    'po-path=', 'settings=', 'message='])
    except getopt.GetoptError:
        usage()
        sys.exit()

    params = _get_params_from_options(opts)
    _set_settings_file(settings, params)

    if command == 'push':
        if 'GIT_MESSAGE' in params:
            return 'push', params['GIT_MESSAGE']
        return 'push', None

    return command, None
