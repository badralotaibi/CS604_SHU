#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask_restful import (Resource, reqparse, Api, abort, inputs, fields,
    marshal)
from flask_httpauth import HTTPBasicAuth
from flask import g
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
    BadSignature, SignatureExpired)

from . import app, db
from .models import User, Student, Parent
from .validators import name, username, email, password, shu_id


profile_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'username': fields.String,
    'email': fields.String,
    'is_admin': fields.Boolean
}

student_fields = {
    'id': fields.Integer,
    'dob': fields.DateTime,
    'shu_id': fields.String,
}

parent_fields = {
    'id': fields.Integer,
    'children': fields.List(fields.Nested(student_fields))
}

auth_fields = {
    'id': fields.Integer,
    'is_admin': fields.Boolean
}


api = Api(app)
auth = HTTPBasicAuth()


parent_parser = reqparse.RequestParser(trim=True)
parent_parser.add_argument('name', type=name, required=True, nullable=False)
parent_parser.add_argument('username', type=username, required=True)
parent_parser.add_argument('email', type=email, required=True)
parent_parser.add_argument('password', type=password, required=True)


student_parser = parent_parser.copy()
student_parser.add_argument('shu_id', type=shu_id, required=True)
student_parser.add_argument('dob', type=inputs.date, required=True)


@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username = username).first()
    if not user or not user.verify_password(password):
        return False
    g.user = user
    return True


class RegisterParent(Resource):
    def post(self):
        args = parent_parser.parse_args(strict=True)
        try:
            user = User(
                name=args.name,
                username=args.username,
                email=args.email
            )
            user.password(args.password)
            parent = Parent(user=user)
            db.session.add_all([user, parent])
            db.session.commit()
            return {'result': 'Parent registered'}, 201
        except Exception, e:
            abort(500)


class RegisterStudent(Resource):
    def post(self):
        args = student_parser.parse_args(strict=True)
        try:
            user = User(
                name=args.name,
                username=args.username,
                email=args.email
            )
            user.password(args.password)
            student = Student(user=user, dob=args.dob, shu_id=args.shu_id)
            db.session.add_all([user, student])
            db.session.commit()
            return {'result': 'Student registered'}, 201
        except Exception, e:
            abort(500)


class Auth(Resource):
    @auth.login_required
    def get(self):
        return marshal(g.user, auth_fields)


class Profile(Resource):
    @auth.login_required
    def get(self):
        user = g.user

        result = {}
        result['profile'] = marshal(user, profile_fields)

        if user.student:
            result['student'] = marshal(user.student, student_fields)

        if user.parent:
            result['parent'] = marshal(user.parent, parent_fields)

        return result


AUTH_PATH = '/auth/%s'
api.add_resource(RegisterParent, AUTH_PATH % 'register-parent')
api.add_resource(RegisterStudent, AUTH_PATH % 'register-student')
api.add_resource(Auth, AUTH_PATH % '')
api.add_resource(Profile, AUTH_PATH % 'profile')
