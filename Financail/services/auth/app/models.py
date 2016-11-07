#!/usr/bin/env python
# -*- coding: utf-8 -*-

from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
    BadSignature, SignatureExpired)

from . import app, db


children = db.Table('children',
    db.Column('parent_id', db.Integer, db.ForeignKey('parents.id')),
    db.Column('student_id', db.Integer, db.ForeignKey('students.id'))
)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(120), unique=True)

    is_admin= db.Column(db.Boolean, default=False)
    _password_hash = db.Column(db.String(500))

    student = db.relationship('Student', back_populates='user', uselist=False)
    parent = db.relationship('Parent', back_populates='user', uselist=False)

    def password(self, password):
        self._password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self._password_hash)


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='student')
    shu_id = db.Column(db.String(12), unique=True)
    dob = db.Column(db.DateTime)


class Parent(db.Model):
    __tablename__ = 'parents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='parent')
    children = db.relationship('Student', secondary=children,
        backref=db.backref('parents', lazy='dynamic'))
