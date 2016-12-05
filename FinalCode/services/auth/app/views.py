#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytz
from datetime import datetime, timedelta, date
from flask_restful import (Resource, reqparse, Api, abort, inputs, fields,
    marshal)
from flask_httpauth import HTTPBasicAuth
from flask_mail import Message
from flask import g, jsonify, request
from itsdangerous import (URLSafeTimedSerializer as Serializer,
  BadSignature, SignatureExpired)
from smtplib import SMTPException
from socket import error as socket_error

from . import app, db, mail
from .models import User, Student, Parent, Child, SystemLoginAttempt
from .validators import (name, username, email, password, shu_id,
    shu_id_not_unique)


parent_fields = {
    'name': fields.String(attribute='parent.user.name'),
    'email': fields.String(attribute='parent.user.email'),
}

child_fields = {
    'name': fields.String(attribute='student.user.name'),
    'email': fields.String(attribute='student.user.email'),
    'dob': fields.DateTime(dt_format='iso8601', attribute='student.dob'),
    'shuId': fields.String(attribute='student.shu_id'),
}

connecting_child_fields = {
    'name': fields.String(attribute='student.user.name'),
    'dob': fields.DateTime(dt_format='iso8601', attribute='student.dob'),
    'shuId': fields.String(attribute='student.shu_id'),
}

student_profile_fields = {
    'dob': fields.DateTime(dt_format='iso8601'),
    'shuId': fields.String(attribute='shu_id'),
    'parents': fields.List(fields.Nested(parent_fields)),
    'connecting': fields.List(fields.Nested(parent_fields))
}

parent_profile_fields = {
    'children': fields.List(fields.Nested(child_fields)),
    'connecting': fields.List(fields.Nested(connecting_child_fields))
}

profile_fields = {
    'name': fields.String,
    'username': fields.String,
    'email': fields.String,
    'isAdmin': fields.Boolean(attribute='is_admin'),
    'isParent': fields.Nested(
        parent_profile_fields, allow_null=True, attribute='parent'
    ),
    'isStudent': fields.Nested(
        student_profile_fields, allow_null=True, attribute='student'
    )
}

login_attempt_fields = {
    'at': fields.DateTime(dt_format='iso8601'),
    'success': fields.Boolean,
    'fromWhere': fields.String(attribute='from_where'),
    'username': fields.String,
    'info': fields.String
}


api = Api(app)
auth = HTTPBasicAuth()
tz = app.config['TZ']

serializer = Serializer(app.config['SECRET_KEY'])

parent_parser = reqparse.RequestParser(trim=True)
parent_parser.add_argument('name', type=name, required=True, nullable=False)
parent_parser.add_argument('username', type=username, required=True)
parent_parser.add_argument('email', type=email, required=True)
parent_parser.add_argument('password', type=password, required=True)


student_parser = parent_parser.copy()
student_parser.add_argument('shu_id', type=shu_id, required=True)
student_parser.add_argument('dob', type=inputs.date, required=True)


def suspend_user(username):
    check_back = datetime.utcnow() - timedelta(
      seconds=app.config['SUSPEND_TIME']
    )

    attempts = SystemLoginAttempt.query.filter(
        SystemLoginAttempt.at >= check_back,
        SystemLoginAttempt.username == username,
        SystemLoginAttempt.success == False
    ).count()

    if (attempts >= app.config['INVALID_LOGIN_ATTEMPTS']):
        suspend = datetime.utcnow() + timedelta(
          seconds=app.config['SUSPEND_TIME']
        )
        user = User.query.filter(User.username==username).first()
        user.suspend = suspend
        db.session.add(user)
        db.session.commit()
        try:
            msg = Message('Account suspended',
                recipients=[user.email])
            msg.body = 'Account "%s (%s)" suspended for %s seconds\n\n' % \
                (user.username, user.email, app.config['SUSPEND_TIME'])
            msg.body += 'There was %s invalid login attempts\n\n' % \
                app.config['INVALID_LOGIN_ATTEMPTS']
            msg.body += 'You can login again after %s' % \
                pytz.utc.localize(suspend).astimezone(tz).strftime(
                  '%Y/%m/%d %H:%M:%S'
                )
            msg.sender = 'noreply@example.com'
            mail.send(msg)
        except SMTPException, e:
            return {'message': str(e)}, 500
        except socket_error, e:
            return {'message': 'smtp socket error: %s' % str(e)}, 500


@auth.verify_password
def verify_password(username_or_token, password):
    try:
        user = User.verify_auth_token(username_or_token)
        if user:
            g.user = user
            return True

        login_attempt = SystemLoginAttempt(from_where=request.remote_addr)

        user = User.query.filter_by(username=username_or_token).first()

        if user and user.suspend and user.suspend >= datetime.utcnow():
            return False

        if user and user.verify_password(password):

            g.user = user

            login_attempt.success = True
            login_attempt.username = user.username

            db.session.add(login_attempt)
            db.session.commit()

            return True
        elif user:
            login_attempt.success = False
            login_attempt.username = user.username
            login_attempt.info = 'Invalid password'

            db.session.add(login_attempt)
            db.session.commit()

            suspend_user(user.username)

            return False
        else:
            login_attempt.success = False
            login_attempt.username = username_or_token
            login_attempt.info = 'Unknown username'

            db.session.add(login_attempt)
            db.session.commit()

            return False
    except Exception, e:
        return False

    return False


class RegisterParent(Resource):
    def post(self):
        args = parent_parser.parse_args(strict=True)

        user = User(
            name=args.name,
            username=args.username,
            email=args.email
        )

        user.set_password(args.password)
        parent = Parent(user=user)
        db.session.add_all([user, parent])
        db.session.commit()
        return {'result': 'Parent registered'}, 201


class RegisterStudent(Resource):
    def post(self):
        args = student_parser.parse_args(strict=True)

        user = User(
            name=args.name,
            username=args.username,
            email=args.email
        )

        user.set_password(args.password)
        student = Student(user=user, dob=args.dob, shu_id=args.shu_id)
        db.session.add_all([user, student])
        db.session.commit()
        return {'result': 'Student registered'}, 201


class ForgetPassword(Resource):
    def post(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('usernameOrEmail', type=str,
          required=True, nullable=False)
        args = parser.parse_args(strict=True)

        user = User.query.filter(User.email==args.usernameOrEmail).first()
        if not user:
            user = User.query.filter(
              User.username==args.usernameOrEmail).first()

        if not user:
            return {'message': 'Username or email not found'}, 404

        token = serializer.dumps(user.email, salt='recover-key')

        try:
            with app.app_context():
                msg = Message('Password reset requested',
                    recipients=[user.email])
                msg.body = 'To reset password follow this link:\n\n'
                msg.body += '%s-%s' % (app.config['RESET_PASSWORD_URL'], token)
                msg.sender = 'noreply@example.com'
                mail.send(msg)
        except SMTPException, e:
            return {'message': str(e)}, 500
        except socket_error, e:
            return {'message': 'smtp socket error: %s' % str(e)}, 500

        return {'emailSent': True}, 200


class ResetPassword(Resource):
    def post(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('token', type=str, required=True,
            nullable=False)
        parser.add_argument('password', type=password,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        try:
            email = serializer.loads(args.token, salt='recover-key',
                max_age=900)
        except (BadSignature, SignatureExpired):
            return {'message': 'Expired or wrong password recovery link'}, 404

        user = User.query.filter_by(email=email).first_or_404()
        user.set_password(args.password)
        db.session.add(user)
        db.session.commit()
        return {'passwordReset': True}, 200


class Auth(Resource):
    def post(self):
        if not request.authorization:
            return {'message': 'Unauthorized'}, 401

        username = request.authorization.get('username', '')
        password = request.authorization.get('password', '')

        if not verify_password(username, password):
            return {'message': 'Wrong username or password'}, 400

        user = g.user
        token, expires = user.generate_auth_token()

        return jsonify({
          'email': user.email,
          'token': token.decode('ascii'),
          'expires': expires,
          'isAdmin': user.is_admin,
          'isStudent': (user.student != None),
          'isParent': (user.parent != None)
        })


class ConnectChild(Resource):
    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('name', type=name, required=True, nullable=False)
        parser.add_argument('dob', type=inputs.date, required=True)
        parser.add_argument('shu_id', type=shu_id_not_unique, required=True)
        args = parser.parse_args(strict=True)

        user = g.user
        if not user.parent:
            return {'message': 'Only parents can call this'}, 403

        student = Student.query.filter_by(
            shu_id=args.shu_id,
            dob=args.dob
        ).first()

        if not student or student.user.name != args.name:
            return {'message': 'Student not found'}, 404

        child = Child.query.filter_by(
            parent=user.parent, student=student).first()

        if not child:
          child = Child(parent=user.parent, student=student)
          db.session.add(child)
          db.session.commit()

        if child.approved:
            return {'message': 'Already connected'}, 409

        token = serializer.dumps(child.id, salt='add-child-request')

        try:
            with app.app_context():
                msg = Message('Parent connection request',
                    recipients=[student.user.email])
                msg.body = 'To accept connection request follow this link:\n\n'
                msg.body += '%s-%s' % (app.config['APPROVE_PARENT_URL'], token)
                msg.sender = 'noreply@example.com'
                mail.send(msg)
        except SMTPException, e:
            return {'message': str(e)}, 500
        except socket_error, e:
            return {'message': 'smtp socket error: %s' % str(e)}, 500

        return {'emailSent': True}, 200


class ApproveParent(Resource):
    @auth.login_required
    def get(self, token):
        user = g.user
        if not user.student:
            return {'message': 'Only students can see this'}, 403

        try:
            child_id = serializer.loads(token, salt='add-child-request')
        except BadSignature:
            return {'message': 'Wrong parent connection link'}, 404

        child = Child.query.filter_by(id=child_id).first()
        if not child:
            return {'message': 'Connection not found'}, 404

        if not user.student == child.student:
            return {'message': 'You can not see this'}, 403

        if child.approved:
          return {'message': 'Already connected'}, 409

        return  marshal(child.parent.user, profile_fields)

    @auth.login_required
    def post(self, token):
        user = g.user
        if not user.student:
            return {'message': 'Only students can see this'}, 403

        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('approved', type=inputs.boolean,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        try:
            child_id = serializer.loads(token, salt='add-child-request')
        except BadSignature:
            return {'message': 'Wrong parent connection link'}, 404

        child = Child.query.filter_by(id=child_id).first()
        if not child:
            return {'message': 'Connection not found'}, 404

        if not user.student == child.student:
            return {'message': 'You can not do this'}, 403

        if child.approved:
          return {'message': 'Already connected'}, 409

        if args.approved:
            try:
                msg = Message('Parent connection accepted',
                    recipients=[child.parent.user.email])
                msg.body = 'You parent connection request'
                msg.body += (' to %s (%s) was accepted.' % (
                    user.name, user.email
                ))
                msg.sender = 'noreply@example.com'
                mail.send(msg)
            except SMTPException, e:
                return {'message': str(e)}, 500
            except socket_error, e:
                return {'message': 'smtp socket error: %s' % str(e)}, 500

            child.approved = True
            db.session.add(child)
            db.session.commit()
            return {
                'approved': True,
                'profile': marshal(user, profile_fields)}, 200
        else:
            db.session.delete(child)
            db.session.commit()
            return {'approved': False}, 200


class CheckParentFor(Resource):
    @auth.login_required
    def get(self):
        uparent = g.user
        if not uparent.parent:
            return { 'isParent': False }

        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('child_email', type=str,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        ustudent = User.query.filter_by(email=args.child_email).first()
        if not ustudent or not ustudent.student:
            return { 'isParent': False }

        child = Child.query.filter_by(
            student_id=ustudent.student.id,
            parent_id=uparent.parent.id
        ).first()

        if not child or not child.approved:
          return { 'isParent': False }

        return { 'isParent': True }


class Profile(Resource):
    @auth.login_required
    def get(self):
        return marshal(g.user, profile_fields)


class LoginAttempts(Resource):
    @auth.login_required
    def get(self):
        if not g.user.is_admin:
            return {'message': 'Only admin can call this'}, 403

        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('date_start', type=inputs.date)
        parser.add_argument('date_end', type=inputs.date)
        parser.add_argument('_', type=str, dest='nocache')
        args = parser.parse_args(strict=True)

        if args.date_start is None:
            args.date_start = date.today()

        if args.date_end is None:
            args.date_end = args.date_start + timedelta(days=1)

        datetime_start = tz.localize(datetime(
          args.date_start.year, args.date_start.month, args.date_start.day)
        )
        datetime_start_utc = datetime_start.astimezone(pytz.utc)

        datetime_end = tz.localize(datetime(
          args.date_end.year, args.date_end.month, args.date_end.day)
        )
        datetime_end_utc = datetime_end.astimezone(pytz.utc)

        attempts = SystemLoginAttempt.query.filter(db.and_(
            SystemLoginAttempt.at >= datetime_start_utc,
            SystemLoginAttempt.at < datetime_end_utc
        )).order_by(SystemLoginAttempt.at.desc()).all()

        return marshal(attempts, login_attempt_fields)


AUTH_PATH = '/auth/%s'
api.add_resource(Auth, AUTH_PATH % '')
api.add_resource(ConnectChild, AUTH_PATH % 'connect-child')
api.add_resource(CheckParentFor, AUTH_PATH % 'check-parent-for')
api.add_resource(ApproveParent, AUTH_PATH % 'approve-parent-<string:token>')
api.add_resource(ForgetPassword, AUTH_PATH % 'forget-password')
api.add_resource(Profile, AUTH_PATH % 'profile')
api.add_resource(RegisterParent, AUTH_PATH % 'register-parent')
api.add_resource(RegisterStudent, AUTH_PATH % 'register-student')
api.add_resource(ResetPassword, AUTH_PATH % 'reset-password')
api.add_resource(LoginAttempts, AUTH_PATH % 'login-attempts')
