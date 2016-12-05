#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import unittest
from base64 import b64encode
from datetime import datetime
from flask_testing import TestCase

os.environ['TESTING'] = 'True'

from app import app, db, mail
from app.models import User, Child


ALICE_NAME = 'Alice'
ALICE_EMAIL = 'alice@example.com'
ALICE_USERNAME = 'alice'
ALICE_PASSWORD = 'Password@123'

BOB_NAME = 'Bob'
BOB_EMAIL = 'bob@example.com'
BOB_USERNAME = 'bob'
BOB_PASSWORD = 'Password@123'
BOB_SHU_ID = '111111111'
BOB_DOB = '2001-03-07'

NOT_BOB_DOB = '2001-01-01'
NOT_BOB_SHU_ID = '111111112'

CAREN_NAME = 'Caren'
CAREN_EMAIL = 'caren@example.com'
CAREN_USERNAME = 'caren'
CAREN_PASSWORD = 'Password@123'
CAREN_SHU_ID = '111111112'
CAREN_DOB = '2001-02-08'

WRONG_PASSWORDS = ['password@123', 'Password123', 'Password@']
WRONG_DOB = '20001-01-01'
WRONG_SHU_ID = '1111111111'


ALICE_DATA = {
    'name': ALICE_NAME,
    'email': ALICE_EMAIL,
    'username': ALICE_USERNAME,
    'password': ALICE_PASSWORD
}

BOB_DATA= {
    'name': BOB_NAME,
    'email': BOB_EMAIL,
    'username': BOB_USERNAME,
    'password': BOB_PASSWORD,
    'shu_id': BOB_SHU_ID,
    'dob': BOB_DOB
}

CAREN_DATA= {
    'name': CAREN_NAME,
    'email': CAREN_EMAIL,
    'username': CAREN_USERNAME,
    'password': CAREN_PASSWORD,
    'shu_id': CAREN_SHU_ID,
    'dob': CAREN_DOB
}


class AuthServiceTest(TestCase):
    # setUp/teardown and helper functions
    def create_app(self):
        return app

    def setUp(self):
        os.environ['ENCRYPTED_TYPE_SECRET_KEY'] = 'test_key'
        db.create_all()

    def tearDown(self):
        if app.config.get('SQLALCHEMY_DATABASE_URI') == 'sqlite://':
            db.drop_all()

    def register_alice(self):
        return self.client.post('/auth/register-parent', data=ALICE_DATA)

    def register_bob(self):
        return self.client.post('/auth/register-student', data=BOB_DATA)

    def register_caren(self):
        return self.client.post('/auth/register-student', data=CAREN_DATA)

    def generate_auth_header(self, username, password):
        return {
            'Authorization':
                'Basic ' + b64encode('%s:%s' % (username, password))
        }

    def make_connection_request(self):
        with mail.record_messages() as outbox:
            self.register_bob()
            self.register_alice()

            headers = self.generate_auth_header(
                ALICE_USERNAME, ALICE_PASSWORD
            )

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            message =  outbox[0].as_string()
            link = message.split('\n')[-1]
            token_start = link.index('#approve-parent-') + 16
            return link[token_start:]

    # Tests for auth service
    def test_register_parent(self):
        response = self.register_alice()
        self.assertEquals(response.status_code, 201)
        self.assertEquals(response.json, {'result': 'Parent registered'})

        alice = User.query.filter(User.email==ALICE_EMAIL).first()
        self.assertEquals(alice.name, ALICE_NAME)
        self.assertEquals(alice.username, ALICE_USERNAME)
        self.assertEquals(alice.email, ALICE_EMAIL)

        self.assertTrue(alice.verify_password(ALICE_PASSWORD))

        self.assertEquals(alice.student, None)
        self.assertNotEquals(alice.parent, None)
        self.assertFalse(alice.is_admin)

    def test_register_parent_wrong_name(self):
        data = ALICE_DATA.copy()
        data['name'] = ''
        response = self.client.post('/auth/register-parent', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('name' in response.json['message'])

    def test_register_parent_wrong_username(self):
        data = ALICE_DATA.copy()
        data['username'] = ''
        response = self.client.post('/auth/register-parent', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('username' in response.json['message'])

    def test_register_parent_wrong_email(self):
        data = ALICE_DATA.copy()
        data['email'] = 'name@com'

        response = self.client.post('/auth/register-parent', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('email' in response.json['message'])

    def test_register_parent_wrong_password(self):
        data = ALICE_DATA.copy()
        for wrong_password in WRONG_PASSWORDS:
            data['password'] = wrong_password

            response = self.client.post('/auth/register-parent', data=data)

            self.assertEquals(response.status_code, 400)
            self.assertTrue('password' in response.json['message'])

    def test_login_parent(self):
        self.register_alice()
        headers = self.generate_auth_header(ALICE_USERNAME, ALICE_PASSWORD)
        response = self.client.post('/auth/', headers=headers)

        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertTrue('token' in result)
        self.assertTrue('expires' in result)
        self.assertFalse(result['isStudent'])
        self.assertTrue(result['isParent'])
        self.assertFalse(result['isAdmin'])
        self.assertEquals(result['email'], ALICE_EMAIL)

    def test_register_student(self):
        response = self.register_bob()
        self.assertEquals(response.status_code, 201)
        self.assertEquals(response.json, {'result': 'Student registered'})

        bob = User.query.filter(User.email==BOB_EMAIL).first()
        self.assertEquals(bob.name, BOB_NAME)
        self.assertEquals(bob.username, BOB_USERNAME)
        self.assertEquals(bob.email, BOB_EMAIL)

        self.assertTrue(bob.verify_password(BOB_PASSWORD))

        self.assertNotEquals(bob.student, None)
        self.assertEquals(bob.parent, None)
        self.assertFalse(bob.is_admin)

        self.assertEquals(bob.student.shu_id, BOB_SHU_ID)
        self.assertEquals(bob.student.dob,
            datetime.strptime(BOB_DOB, '%Y-%m-%d'))

    def test_register_student_wrong_name(self):
        data = BOB_DATA.copy()
        data['name'] = ''
        response = self.client.post('/auth/register-student', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('name' in response.json['message'])

    def test_register_student_wrong_username(self):
        data = BOB_DATA.copy()
        data['username'] = ''
        response = self.client.post('/auth/register-student', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('username' in response.json['message'])

    def test_register_student_wrong_email(self):
        data = BOB_DATA.copy()
        data['email'] = 'name@com'

        response = self.client.post('/auth/register-student', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('email' in response.json['message'])

    def test_register_student_wrong_password(self):
        data = BOB_DATA.copy()
        for wrong_password in WRONG_PASSWORDS:
            data['password'] = wrong_password

            response = self.client.post('/auth/register-student', data=data)

            self.assertEquals(response.status_code, 400)
            self.assertTrue('password' in response.json['message'])

    def test_register_student_wrong_dob(self):
        data = BOB_DATA.copy()
        data['dob'] = WRONG_DOB

        response = self.client.post('/auth/register-student', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('dob' in response.json['message'])

    def test_register_student_wrong_shu_id(self):
        data = BOB_DATA.copy()
        data['shu_id'] = WRONG_SHU_ID

        response = self.client.post('/auth/register-student', data=data)

        self.assertEquals(response.status_code, 400)
        self.assertTrue('shu_id' in response.json['message'])

    def test_register_username_already_registered(self):
        self.register_bob()

        data = BOB_DATA.copy()
        data['email'] = 'another.' + BOB_EMAIL
        data['shu_id'] = str(int(BOB_SHU_ID) + 15)
        response = self.client.post('/auth/register-student', data=data)
        self.assertEquals(response.status_code, 400)
        self.assertTrue('username' in response.json['message'])

    def test_register_email_already_registered(self):
        self.register_bob()

        data = BOB_DATA.copy()
        data['username'] = 'another.' + BOB_USERNAME
        data['shu_id'] = str(int(BOB_SHU_ID) + 15)
        response = self.client.post('/auth/register-student', data=data)
        self.assertEquals(response.status_code, 400)
        self.assertTrue('email' in response.json['message'])

    def test_register_shu_id_already_registered(self):
        self.register_bob()

        data = BOB_DATA.copy()
        data['username'] = 'another.' + BOB_USERNAME
        data['email'] = 'another.' + BOB_EMAIL
        response = self.client.post('/auth/register-student', data=data)
        self.assertEquals(response.status_code, 400)
        self.assertTrue('shu_id' in response.json['message'])

    def test_login_student(self):
        self.register_bob()
        headers = self.generate_auth_header(BOB_USERNAME, BOB_PASSWORD)
        response = self.client.post('/auth/', headers=headers)

        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertTrue('token' in result)
        self.assertTrue('expires' in result)
        self.assertTrue(result['isStudent'])
        self.assertFalse(result['isParent'])
        self.assertFalse(result['isAdmin'])
        self.assertEquals(result['email'], BOB_EMAIL)

    def test_login_wrong_username(self):
        self.register_bob()
        headers = self.generate_auth_header(BOB_USERNAME, BOB_PASSWORD + 'typo')
        response = self.client.post('/auth/', headers=headers)

        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertEquals(result['message'], 'Wrong username or password')

    def test_login_wrong_password(self):
        self.register_bob()
        headers = self.generate_auth_header(BOB_USERNAME + 'typo', BOB_PASSWORD)
        response = self.client.post('/auth/', headers=headers)

        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertEquals(result['message'], 'Wrong username or password')

    def test_login_with_token(self):
        self.register_bob()
        headers = self.generate_auth_header(BOB_USERNAME, BOB_PASSWORD)
        response = self.client.post('/auth/', headers=headers)

        result = response.json

        headers = self.generate_auth_header(result['token'], 'x')

        response = self.client.post('/auth/', headers=headers)

        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertTrue('token' in result)
        self.assertTrue('expires' in result)
        self.assertTrue(result['isStudent'])
        self.assertFalse(result['isParent'])
        self.assertFalse(result['isAdmin'])
        self.assertEquals(result['email'], BOB_EMAIL)

    def test_login_expired_token(self):
        self.register_bob()
        headers = self.generate_auth_header(BOB_USERNAME, BOB_PASSWORD)
        response = self.client.post('/auth/', headers=headers)

        result = response.json
        headers = self.generate_auth_header(result['token'], 'x')

        time.sleep(6)

        response = self.client.post('/auth/', headers=headers)

        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertEquals(result['message'], 'Wrong username or password')

    def test_suspend_user(self):
        with mail.record_messages() as outbox:
            self.register_bob()
            headers = self.generate_auth_header(BOB_USERNAME, BOB_PASSWORD + 'typo')

            self.assertEquals(len(outbox), 0)
            response = self.client.post('/auth/', headers=headers)
            response = self.client.post('/auth/', headers=headers)
            response = self.client.post('/auth/', headers=headers)

            self.assertEquals(len(outbox), 1)
            self.assertTrue('Account "%s (%s)" suspended' % (
                BOB_USERNAME, BOB_EMAIL
            ) in outbox[0].as_string())

            headers = self.generate_auth_header(BOB_USERNAME, BOB_PASSWORD)

            response = self.client.post('/auth/', headers=headers)
            self.assertEquals(response.status_code, 400)

            time.sleep(5)

            response = self.client.post('/auth/', headers=headers)
            self.assertEquals(response.status_code, 200)

    def test_forget_password_unknown(self):
        with mail.record_messages() as outbox:
            self.register_bob()

            self.assertEquals(len(outbox), 0)
            response = self.client.post('/auth/forget-password', data={
                'usernameOrEmail': 'not.' + BOB_USERNAME
            })
            self.assertEquals(len(outbox), 0)
            self.assertEquals(response.status_code, 404)
            self.assertTrue('not found' in response.json['message'])

            self.assertEquals(len(outbox), 0)
            response = self.client.post('/auth/forget-password', data={
                'usernameOrEmail': 'not.' + 'not.' + BOB_EMAIL
            })
            self.assertEquals(len(outbox), 0)
            self.assertEquals(response.status_code, 404)
            self.assertTrue('not found' in response.json['message'])

    def test_forget_password_by_username(self):
        with mail.record_messages() as outbox:
            self.register_bob()

            self.assertEquals(len(outbox), 0)
            response = self.client.post('/auth/forget-password', data={
                'usernameOrEmail': BOB_USERNAME
            })
            self.assertEquals(len(outbox), 1)
            self.assertTrue('follow this link' in outbox[0].as_string())

    def test_forget_password_by_email(self):
        with mail.record_messages() as outbox:
            self.register_bob()

            self.assertEquals(len(outbox), 0)
            response = self.client.post('/auth/forget-password', data={
                'usernameOrEmail': BOB_EMAIL
            })
            self.assertEquals(len(outbox), 1)
            self.assertTrue('follow this link' in outbox[0].as_string())

    def test_reset_password(self):
        with mail.record_messages() as outbox:
            self.register_bob()

            self.assertEquals(len(outbox), 0)
            response = self.client.post('/auth/forget-password', data={
                'usernameOrEmail': BOB_EMAIL
            })
            self.assertEquals(len(outbox), 1)
            message = outbox[0].as_string()
            self.assertTrue('follow this link' in message)

            link = message.split('\n')[-1]
            token_start = link.index('#reset-password-') + 16
            token = link[token_start:]

            for wrong_password in WRONG_PASSWORDS:
                response = self.client.post('/auth/reset-password', data={
                    'token': token,
                    'paswword': wrong_password
                })
                self.assertEquals(response.status_code, 400)
                self.assertTrue('password' in response.json['message'])

            response = self.client.post('/auth/reset-password', data={
                'token': token,
                'password': BOB_PASSWORD[:-2]
            })
            self.assertEquals(response.status_code, 200)

            headers = self.generate_auth_header(
                BOB_USERNAME, BOB_PASSWORD[:-2]
            )
            response = self.client.post('/auth/', headers=headers)
            self.assertEquals(response.status_code, 200)

            self.assertTrue('token' in response.json)
            self.assertEquals(response.json['email'], BOB_EMAIL)

    def test_connect_child_by_student(self):
        with mail.record_messages() as outbox:
            self.register_bob()
            self.register_alice()

            headers = self.generate_auth_header(
                BOB_USERNAME, BOB_PASSWORD
            )

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            self.assertEquals(response.status_code, 403)
            self.assertTrue('Only parents' in response.json['message'])

    def test_connect_child_wrong_data(self):
        with mail.record_messages() as outbox:
            self.register_bob()
            self.register_alice()

            headers = self.generate_auth_header(
                ALICE_USERNAME, ALICE_PASSWORD
            )

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME + 'typo',
                'dob': BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            self.assertEquals(response.status_code, 404)
            self.assertTrue('not found' in response.json['message'])

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': NOT_BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            self.assertEquals(response.status_code, 404)
            self.assertTrue('not found' in response.json['message'])

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': BOB_DOB,
                'shu_id': NOT_BOB_SHU_ID
            }, headers=headers)
            self.assertEquals(response.status_code, 404)
            self.assertTrue('not found' in response.json['message'])

    def test_connect_child_already_connected(self):
        with mail.record_messages() as outbox:
            self.register_bob()
            self.register_alice()

            headers = self.generate_auth_header(
                ALICE_USERNAME, ALICE_PASSWORD
            )

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            child = Child.query.first()
            child.approved = True
            db.session.add(child)
            db.session.commit()

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            self.assertEquals(response.status_code, 409)
            self.assertTrue('Already connected' in response.json['message'])

    def test_connect_child(self):
        with mail.record_messages() as outbox:
            self.register_bob()
            self.register_alice()

            headers = self.generate_auth_header(
                ALICE_USERNAME, ALICE_PASSWORD
            )

            response = self.client.post('/auth/connect-child', data={
                'name': BOB_NAME,
                'dob': BOB_DOB,
                'shu_id': BOB_SHU_ID
            }, headers=headers)
            self.assertEquals(response.status_code, 200)
            self.assertTrue('emailSent' in response.json)
            self.assertEquals(len(outbox), 1)
            self.assertTrue('follow this link' in outbox[0].as_string())

    def test_approve_parent_get_by_parent(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )

        response = self.client.get('/auth/approve-parent-' + token,
            headers=headers)
        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only students' in response.json['message'])

    def test_approve_parent_get_wrong_token(self):
        token = self.make_connection_request() + 'typo'

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.get('/auth/approve-parent-' + token,
            headers=headers)
        self.assertEquals(response.status_code, 404)
        self.assertTrue('Wrong' in response.json['message'])

    def test_approve_parent_get_deleted_child_request(self):
        token = self.make_connection_request()

        child = Child.query.first()
        db.session.delete(child)
        db.session.commit()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.get('/auth/approve-parent-' + token,
            headers=headers)
        self.assertEquals(response.status_code, 404)
        self.assertTrue('not found' in response.json['message'])

    def test_approve_parent_get_other_student(self):
        token = self.make_connection_request()
        self.register_caren()

        headers = self.generate_auth_header(
            CAREN_USERNAME, CAREN_PASSWORD
        )
        response = self.client.get('/auth/approve-parent-' + token,
            headers=headers)
        self.assertEquals(response.status_code, 403)
        self.assertTrue('can not see this' in response.json['message'])

    def test_approve_parent_get_already_connected(self):
        token = self.make_connection_request()

        child = Child.query.first()
        child.approved = True
        db.session.add(child)
        db.session.commit()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.get('/auth/approve-parent-' + token,
            headers=headers)
        self.assertEquals(response.status_code, 409)
        self.assertTrue('Already connected' in response.json['message'])

    def test_approve_parent_get(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.get('/auth/approve-parent-' + token,
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['username'], ALICE_USERNAME)
        self.assertEquals(result['name'], ALICE_NAME)
        self.assertEquals(result['email'], ALICE_EMAIL)

    def test_approve_parent_post_by_parent(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )

        response = self.client.post('/auth/approve-parent-' + token,
            headers=headers)
        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only students' in response.json['message'])

    def test_approve_parent_post_wrong_token(self):
        token = self.make_connection_request() + 'typo'

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.post('/auth/approve-parent-' + token,
            data = {'approved': 'True'},
            headers=headers)
        self.assertEquals(response.status_code, 404)
        self.assertTrue('Wrong' in response.json['message'])

    def test_approve_parent_post_deleted_child_request(self):
        token = self.make_connection_request()

        child = Child.query.first()
        db.session.delete(child)
        db.session.commit()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.post('/auth/approve-parent-' + token,
            data = {'approved': 'True'},
            headers=headers)
        self.assertEquals(response.status_code, 404)
        self.assertTrue('not found' in response.json['message'])

    def test_approve_parent_post_other_student(self):
        token = self.make_connection_request()
        self.register_caren()

        headers = self.generate_auth_header(
            CAREN_USERNAME, CAREN_PASSWORD
        )
        response = self.client.post('/auth/approve-parent-' + token,
            data = {'approved': 'True'},
            headers=headers)
        self.assertEquals(response.status_code, 403)
        self.assertTrue('can not do this' in response.json['message'])

    def test_approve_parent_post_already_connected(self):
        token = self.make_connection_request()

        child = Child.query.first()
        child.approved = True
        db.session.add(child)
        db.session.commit()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/auth/approve-parent-' + token,
            data = {'approved': 'True'},
            headers=headers)
        self.assertEquals(response.status_code, 409)
        self.assertTrue('Already connected' in response.json['message'])

    def test_approve_parent_post_decline(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/auth/approve-parent-' + token,
            data = {'approved': 'False'},
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['approved'], False)

        child = Child.query.first()
        self.assertEquals(child, None)

    def test_approve_parent_post_approve(self):
        token = self.make_connection_request()

        with mail.record_messages() as outbox:
            headers = self.generate_auth_header(
                BOB_USERNAME, BOB_PASSWORD
            )

            response = self.client.post('/auth/approve-parent-' + token,
                data = {'approved': 'True'},
                headers=headers)
            result = response.json

            child = Child.query.first()
            self.assertEquals(child.approved, True)

            self.assertEquals(response.status_code, 200)
            self.assertEquals(result['approved'], True)
            self.assertEquals(
                result['profile']['isStudent']['parents'][0]['name'],
                ALICE_NAME)

            self.assertEquals(len(outbox), 1)
            self.assertTrue('was accepted' in outbox[0].as_string())

    def test_check_parent_for_if_student(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.get('/auth/check-parent-for',
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['isParent'], False)

    def test_check_parent_for_if_no_user(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )

        response = self.client.get('/auth/check-parent-for',
            data = {'child_email': 'anonther.' + BOB_EMAIL},
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['isParent'], False)

    def test_check_parent_for_if_user_is_parent(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )

        response = self.client.get('/auth/check-parent-for',
            data = {'child_email': ALICE_EMAIL},
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['isParent'], False)

    def test_check_parent_for_if_parent_not_approved(self):
        token = self.make_connection_request()

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )

        response = self.client.get('/auth/check-parent-for',
            data = {'child_email': BOB_EMAIL},
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['isParent'], False)

    def test_check_parent_for_if_parent_approved(self):
        token = self.make_connection_request()

        child = Child.query.first()
        child.approved = True
        db.session.add(child)
        db.session.commit()

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )

        response = self.client.get('/auth/check-parent-for',
            data = {'child_email': BOB_EMAIL},
            headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['isParent'], True)

    def test_profile(self):
        token = self.make_connection_request()
        child = Child.query.first()
        child.approved = True
        db.session.add(child)
        db.session.commit()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.get('/auth/profile',
            headers=headers)
        result = response.json
        self.assertEquals(response.status_code, 200)
        self.assertEquals(
            result['isStudent']['parents'][0]['name'], ALICE_NAME)

    def test_login_attempts_not_admin(self):
        self.register_bob()
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.get('/auth/login-attempts',
            headers=headers)
        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only admin' in response.json['message'])

    def test_login_attempts(self):
        self.register_bob()

        bob = User.query.filter(User.email==BOB_EMAIL).first()
        bob.is_admin = True
        db.session.add(bob)
        db.session.commit()

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD + 'typo'
        )
        response = self.client.post('/auth/', headers=headers)
        self.assertEquals(response.status_code, 400)

        headers = self.generate_auth_header(
            BOB_USERNAME + 'typo', BOB_PASSWORD
        )
        response = self.client.post('/auth/', headers=headers)
        self.assertEquals(response.status_code, 400)

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/auth/', headers=headers)
        self.assertEquals(response.status_code, 200)

        headers = self.generate_auth_header(
            response.json['token'], 'x'
        )
        response = self.client.get('/auth/login-attempts',
            headers=headers)
        self.assertEquals(response.status_code, 200)
        result = response.json
        self.assertEquals(len(result), 3)
        self.assertEquals(result[-1]['success'], False)
        self.assertEquals(result[-1]['info'], 'Invalid password')
        self.assertEquals(result[-2]['success'], False)
        self.assertEquals(result[-2]['info'], 'Unknown username')
        self.assertEquals(result[-3]['success'], True)


if __name__ == '__main__':
    unittest.main()
