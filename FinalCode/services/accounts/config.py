#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from pytz import timezone


DEBUG = True
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = '-pzdsv$cuc!$1!_@#38)&rt!-bt+z9-z9!#3th+sn$mhz__)@j'
MASTER_PASSWORD_KEY_NAME = 'MASTER_PASSWORD'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
SQLALCHEMY_COMMIT_ON_TEARDOWN = True
SQLALCHEMY_TRACK_MODIFICATIONS = False

AUTH_SERVICE_URL = 'http://localhost:5001/auth/'

DEPOSIT_ACCOUNT = 'DEPOSIT'
SPENDING_ACCOUNT = 'SPENDING'

TZ = timezone('EST')
ENCRYPTED_TYPE_SECRET_KEY = 'some secret key'
