#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

app = Flask(__name__)
if os.environ.get('TESTING', 'False') == 'True':
  app.config.from_object('test_config')
else:
  app.config.from_object('config')

db = SQLAlchemy(app)
mail = Mail(app)

from . import views, models
