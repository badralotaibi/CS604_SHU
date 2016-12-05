#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pytz
from datetime import datetime, date
from passlib.apps import custom_app_context as pwd_context
from sqlalchemy.sql import func
from sqlalchemy_utils import EncryptedType

from . import app, db


tz = app.config['TZ']


def get_secret_key():
    return os.environ.get('ENCRYPTED_TYPE_SECRET_KEY', None)


class SystemKey(db.Model):
    __tablename__ = 'system_keys'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), unique=True)

    _password_hash = db.Column(db.String(500))

    def set_password(self, password):
        self._password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self._password_hash)


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(EncryptedType(
        db.String(120), get_secret_key), unique=True)

    balance = db.Column(EncryptedType(
        db.Float(precision=2, as_decimal=True), get_secret_key), default=.0)

    daily_limit = db.Column(EncryptedType(
        db.Float(precision=0, as_decimal=True), get_secret_key), default=.0)

    def spent_today(self):
        today = date.today()
        today_start = tz.localize(datetime(today.year, today.month, today.day))
        today_start_utc = today_start.astimezone(pytz.utc)

        amount = db.session.query(
            func.sum(Transaction.amount)
        ).filter(
            Transaction.created >= today_start_utc,
            Transaction.credit_id == self.id
        ).scalar()

        if amount is None:
            amount = 0.0

        return amount


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)

    created = db.Column(db.DateTime, default=datetime.utcnow)

    amount = db.Column(db.Float(precision=2, as_decimal=True))

    memo = db.Column(EncryptedType(
        db.String(256), get_secret_key))

    credit_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))

    credit = db.relationship('Account', foreign_keys=[credit_id])

    debit_id = db.Column(db.Integer, db.ForeignKey('accounts.id'))

    debit = db.relationship('Account', foreign_keys=[debit_id])
