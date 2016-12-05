#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from .models import User, Student


HOSTNAME_PART_RE = re.compile(r'^(xn-|[a-z0-9]+)(-[a-z0-9]+)*$',
    re.IGNORECASE)

TLD_PART_RE = re.compile(r'^([a-z]{2,20}|xn--([a-z0-9]+-)*[a-z0-9]+)$',
    re.IGNORECASE)

EMAIL_RE = re.compile(r'^.+@([^.@][^@]+)$', re.IGNORECASE)

SHU_ID_RE = re.compile(r'^\d{9}$', re.IGNORECASE)


def name(val):
    if len(val) < 1:
        raise TypeError('Name should not be void')

    return val


def username(val):
    if len(val) < 3:
        raise TypeError('{}: username is shorter than 3 letter'.format(val))

    if User.query.filter(User.username==val).all():
        raise TypeError('{}: username is already registered'.format(val))

    return val


def email(val):
    match = EMAIL_RE.match(val)

    if not match:
        raise TypeError('{}: is not a valid email'.format(val))

    hostname(match.group(1))

    if User.query.filter(User.email==val).all():
        raise TypeError('{}: email is already registered'.format(val))

    return val


def password(val):

    if not 8 <= len(val) <= 12:
        raise TypeError('password must be 8-12 characters long')

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
        raise TypeError('password must contain at least '
                        'one digit, one uppercase character '
                        'and one special character')
    return val

def shu_id_not_unique(val):
    match = SHU_ID_RE.match(val)

    if not match:
        raise TypeError('{} is not a valid SHU ID'.format(val))

    return val

def shu_id(val):
    shu_id_not_unique(val)

    if Student.query.filter(Student.shu_id==val).all():
        raise TypeError('{}: SHU ID is already registered'.format(val))

    return val


def hostname(val):
    if len(val) > 253:
        raise TypeError('{} is not a valid hostname'.format(val))

    parts = val.split('.')
    for part in parts:
        if not part or len(part) > 63:
            raise TypeError('{} is not a valid hostname'.format(val))
        if not HOSTNAME_PART_RE.match(part):
            raise TypeError('{} is not a valid hostname'.format(val))

    if len(parts) < 2 or not TLD_PART_RE.match(parts[-1]):
        raise TypeError('{} is not a valid hostname'.format(val))

    return val
