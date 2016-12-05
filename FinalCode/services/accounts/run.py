#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import colorama
from app import app, db, models
from getpass import getpass


key = app.config.get('ENCRYPTED_TYPE_SECRET_KEY', None)
if key:
    os.environ['ENCRYPTED_TYPE_SECRET_KEY'] = key


def check_password_strong(val):
    if not 8 <= len(val):
        print colorama.Fore.RED + 'Password must be minimum 8 characters long'
        print colorama.Style.RESET_ALL
        return False

    upper = digit = special = 0

    for c in val:
        if c.isalpha():
            if c.isupper():
                upper += 1
        elif c.isdigit():
            digit += 1
        else:
            special += 1

    if not upper or not digit or not special:
        print colorama.Fore.RED + 'Password must contain at least' + \
                                  ' one digit, one uppercase character' + \
                                  ' and one special character'
        print colorama.Style.RESET_ALL

        return False

    return True


def create_master_password():
    print colorama.Fore.YELLOW + 'System need new master password' + \
                                 ' to encrypt data'
    print colorama.Fore.RED + 'Warning: remember master password' + \
                              ' or all data will be lost'
    print colorama.Style.RESET_ALL

    while True:
        key = getpass('Enter New Master Password: ')
        if not check_password_strong(key):
            continue

        key_confirmed = getpass('Confirm Master Password: ')

        if key != key_confirmed:
            print colorama.Fore.RED + 'Passwords differ, try again.'
            print colorama.Style.RESET_ALL
            continue

        break
    print colorama.Fore.YELLOW + 'Master password hash stored in database' + \
                                 ' to check it correctness on the next startup'
    print colorama.Style.RESET_ALL

    master_key = models.SystemKey(name=app.config['MASTER_PASSWORD_KEY_NAME'])
    master_key.set_password(key)
    db.session.add(master_key)
    db.session.commit()

    os.environ['ENCRYPTED_TYPE_SECRET_KEY'] = key


def enter_master_password(master_key):
    print colorama.Fore.YELLOW + 'System need master password to decrypt data'
    print colorama.Style.RESET_ALL
    while True:
        key = getpass('Enter Master Password: ')
        if master_key.verify_password(key):
            os.environ['ENCRYPTED_TYPE_SECRET_KEY'] = key
            return
        else:
            print colorama.Fore.RED + 'Wrong password'
            print colorama.Style.RESET_ALL


def get_password():
    colorama.init()
    master_key = models.SystemKey.query.filter(
        models.SystemKey.name == app.config['MASTER_PASSWORD_KEY_NAME']
    ).first()

    if not master_key:
        create_master_password()
    else:
        enter_master_password(master_key)


if __name__ == "__main__":
    db.create_all()
    if not os.environ.get('ENCRYPTED_TYPE_SECRET_KEY', False):
        get_password()
    app.run(port=5002)
