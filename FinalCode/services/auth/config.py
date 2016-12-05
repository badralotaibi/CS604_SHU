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

RESET_PASSWORD_URL = 'http://localhost:5000/#reset-password'
APPROVE_PARENT_URL = 'http://localhost:5000/#approve-parent'

AUTH_TOKEN_EXPIRES = 300
INVALID_LOGIN_ATTEMPTS = 3
SUSPEND_TIME = 60

ADMIN_NAME = 'System Administrator'
ADMIN_EMAIL = 'admin@example.com'

TZ = timezone('EST')

ENCRYPTED_TYPE_SECRET_KEY = 'some secret key'
ADMIN_PASSWORD = 'some secret admin key'
