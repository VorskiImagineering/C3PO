#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mod import initializer
# need to prepare settings before importing anything
command = initializer.initialize()
from mod import communicator
from mod.communicator import git_push, git_checkout
from mod.initializer import ALLOWED_COMMANDS


def main():
    if command[0] == 'push':
        git_push(command[1])
    elif command[0] == 'checkout':
        git_checkout()
    elif command[0] in ALLOWED_COMMANDS:
        com = communicator.Communicator()
        getattr(com, command[0])()


if __name__ == '__main__':
    main()
