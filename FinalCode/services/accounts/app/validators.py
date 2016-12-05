#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re


CARD_NUMBER_RE = re.compile(
    r'^([0-9]{4})[ -]?([0-9]{4})[ -]?([0-9]{4})[ -]?([0-9]{4})$', re.IGNORECASE)

CVC_RE = re.compile(r'^[0-9]{3}$', re.IGNORECASE)

AMOUNT_RE = re.compile(r'^\d+(\.\d{1,2})?$', re.IGNORECASE)


def card_number(val):
    match = CARD_NUMBER_RE.match(val)
    if not match:
        raise TypeError('{} is not a valid card number'.format(val))

    return ''.join(match.groups())


def exp_year(val):
    try:
        val = int(val)
    except:
        raise TypeError('{} is not a valid expiration year'.format(val))

    if not 0 <= val <= 99:
        raise TypeError('{} is not a valid expiration year'.format(val))

    return val


def exp_month(val):
    try:
        val = int(val)
    except:
        raise TypeError('{} is not a valid expiration month'.format(val))

    if not 1 <= val <= 12:
        raise TypeError('{} is not a valid expiration month'.format(val))

    return val


def cvc(val):
    match = CVC_RE.match(val)
    if not match:
        raise TypeError('{} is not a valid CVC'.format(val))

    return val


def positive_amount(val):
    match = AMOUNT_RE.match(val)
    if not match:
        raise TypeError('{} is not a valid amount'.format(val))

    val = float(val)

    if not val > 0:
        raise TypeError('amount must be positive')

    return val

def limit_amount(val):
    match = AMOUNT_RE.match(val)
    if not match:
        raise TypeError('{} is not a valid amount'.format(val))

    return float(val)
