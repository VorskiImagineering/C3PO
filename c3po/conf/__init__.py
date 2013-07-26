#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

import settings_default


class Singleton(type):
    def __init__(cls, name, bases, sdict):
        super(Singleton, cls).__init__(name, bases, sdict)
        cls.instance = None

    def __call__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance


class SettingsWrapper(object):
    __metaclass__ = Singleton

    settings_dict = {}
    custom_dict = {}

    def __init__(self):
        super(SettingsWrapper, self).__init__()
        self.settings_dict = self.module_to_dict(settings_default)
        self.configure()

    def dict_to_attrs(self, sdict):
        for k, v in sdict.items():
            setattr(self, k, v)

    def configure(self):
        sdict = self.settings_dict
        sdict.update(self.custom_dict)
        self.dict_to_attrs(sdict)

    @classmethod
    def module_to_dict(cls, module):
        cdict = {}
        for attr in dir(module):
            if attr.startswith('_'):
                continue
            cdict[attr] = getattr(module, attr)
        return cdict

    def set_config(self, custom_settings_path, params):
        cs_path, cs_name = os.path.split(custom_settings_path)
        if cs_name.endswith('.py'):
            cs_name = cs_name[:-3]
        sys.path.insert(0, cs_path)
        custom_settings = __import__(cs_name)
        sys.path = sys.path[1:]
        self.custom_dict = self.module_to_dict(custom_settings)
        self.custom_dict.update(params)
        self.configure()

    def print_settings(self):
        for attr in dir(self):
            if not attr.startswith('_'):
                print attr, getattr(self, attr)


settings = SettingsWrapper()
