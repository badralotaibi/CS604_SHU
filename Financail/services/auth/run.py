#!/usr/bin/env python
# -*- coding: utf-8 -*-

from app import app, db

db.create_all()
app.run(port=5001)
