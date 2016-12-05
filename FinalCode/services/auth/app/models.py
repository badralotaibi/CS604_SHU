#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from datetime import datetime
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
  BadSignature, SignatureExpired)
from sqlalchemy_utils import EncryptedType

from . import app, db


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


class SystemLoginAttempt(db.Model):
    __tablename__ = 'system_login_attempts'

    id = db.Column(db.Integer, primary_key=True)

    at = db.Column(db.DateTime, default=datetime.utcnow)

    success = db.Column(db.Boolean)

    from_where = db.Column(EncryptedType(db.String(120), get_secret_key))

    username = db.Column(EncryptedType(db.String(120), get_secret_key))

    info = db.Column(EncryptedType(db.String(120), get_secret_key))


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    suspend = db.Column(db.DateTime)

    name = db.Column(EncryptedType(
        db.String(120), get_secret_key))

    username = db.Column(EncryptedType(
        db.String(64), get_secret_key), unique=True)

    email = db.Column(EncryptedType(
        db.String(120), get_secret_key), unique=True)

    is_admin = db.Column(db.Boolean, default=False)

    _password_hash = db.Column(db.String(500))

    student = db.relationship('Student', back_populates='user', uselist=False)
    parent = db.relationship('Parent', back_populates='user', uselist=False)

    def set_password(self, password):
        self._password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self._password_hash)

    def generate_auth_token(self, expires=app.config['AUTH_TOKEN_EXPIRES']):
        s = Serializer(app.config['SECRET_KEY'], expires_in=expires)
        return s.dumps({ 'id': self.id }), expires

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except (SignatureExpired, BadSignature):
            return None
        user = User.query.get(data['id'])
        return user


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    user = db.relationship('User', back_populates='student')

    shu_id = db.Column(EncryptedType(
        db.String(12), get_secret_key), unique=True)

    dob = db.Column(EncryptedType(
        db.DateTime, get_secret_key))

    parents = db.relationship('Child', back_populates='student',
        primaryjoin='and_(Child.student_id==Student.id, Child.approved==True)')

    connecting = db.relationship('Child', back_populates='student',
        primaryjoin='and_(Child.student_id==Student.id, Child.approved==False)')


class Parent(db.Model):
    __tablename__ = 'parents'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    user = db.relationship('User', back_populates='parent')

    children = db.relationship('Child', back_populates='parent',
        primaryjoin='and_(Child.parent_id==Parent.id, Child.approved==True)')

    connecting = db.relationship('Child', back_populates='parent',
        primaryjoin='and_(Child.parent_id==Parent.id, Child.approved==False)')


class Child(db.Model):
    __tablename__ = 'children'
    __table_args__ = (
      db.UniqueConstraint('parent_id', 'student_id', name='_parent_student_uc'),
    )

    id = db.Column(db.Integer, primary_key=True)

    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'),
        nullable=False)

    parent = db.relationship('Parent', back_populates='children')

    student_id = db.Column(db.Integer, db.ForeignKey('students.id'),
        nullable=False)

    student = db.relationship('Student', back_populates='parents')

    approved = db.Column(db.Boolean, default=False)
