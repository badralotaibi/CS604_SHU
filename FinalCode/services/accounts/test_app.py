#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import unittest
from base64 import b64encode
from flask_testing import TestCase
from mock import patch

os.environ['TESTING'] = 'True'

from app import app, db, mail
from app.models import Account, Transaction

ALICE_EMAIL = 'alice@example.com'
ALICE_USERNAME = 'alice'
ALICE_PASSWORD = 'Password@123'

BOB_EMAIL = 'bob@example.com'
BOB_USERNAME = 'bob'
BOB_PASSWORD = 'Password@123'

CAREN_EMAIL = 'caren@example.com'
CAREN_USERNAME = 'caren'
CAREN_PASSWORD = 'Password@123'

DAILY_LIMIT = 50.0

CARD_NUMBER = '1234-5678-9012-3456'
EXP_YEAR = 19
EXP_YEAR_WRONG = 16
EXP_MONTH = 11
CVC = 123

DEPOSIT_ACCOUNT = app.config['DEPOSIT_ACCOUNT']
SPENDING_ACCOUNT = app.config['SPENDING_ACCOUNT']


class AuthResponse():
    def __init__(self, username='', email='', isStudent=False, isParent=False):
        self.status_code = 200
        self.username = username
        self.email = email
        self.isParent = isParent
        self.isStudent = isStudent

    def json(self):
        return {
            'email': self.email,
            'expires': 300,
            'isAdmin': False,
            'isParent': self.isParent,
            'isStudent': self.isStudent,
            'token': self.username
        }


class WrongAuthResponse():
    def __init__(self):
        self.status_code = 401


def auth_mock(*args, **kwargs):
    username = kwargs['auth'].username
    password = kwargs['auth'].password

    if username == ALICE_USERNAME and password == ALICE_PASSWORD:
        return AuthResponse(ALICE_USERNAME, ALICE_EMAIL, False, True)

    if username == BOB_USERNAME and password == BOB_PASSWORD:
        return AuthResponse(BOB_USERNAME, BOB_EMAIL, True)

    if username == CAREN_USERNAME and password == CAREN_PASSWORD:
        return AuthResponse(CAREN_USERNAME, CAREN_EMAIL, True)

    return WrongAuthResponse()


class CheckParentResponse():
    def __init__(self, isParent):
        self.status_code = 200
        self.isParent = isParent

    def json(self):
        return {'isParent': self.isParent}


def check_parent_mock(*args, **kwargs):
    username = kwargs['auth'].username
    child_email = json.loads((kwargs['data']))['child_email']

    if not username == ALICE_USERNAME:
        return CheckParentResponse(False)

    if not child_email == BOB_EMAIL:
        return CheckParentResponse(False)

    return CheckParentResponse(True)


@patch('app.views.requests.get', side_effect=check_parent_mock)
@patch('app.views.requests.post', side_effect=auth_mock)
class AccountsServiceTest(TestCase):
    # setUp/teardown and helper functions
    def create_app(self):
        return app

    def setUp(self):
        os.environ['ENCRYPTED_TYPE_SECRET_KEY'] = 'test_key'
        db.create_all()

    def tearDown(self):
        if app.config.get('SQLALCHEMY_DATABASE_URI') == 'sqlite://':
            db.drop_all()

    def generate_auth_header(self, username, password):
        return {
            'Authorization':
                'Basic ' + b64encode('%s:%s' % (username, password))
        }

    def create_account(self, username, password):
        headers = self.generate_auth_header(
            username, password
        )
        self.client.post('/acc/', headers=headers)

    def deposit(self, username, password, amount):
        headers = self.generate_auth_header(
            username, password
        )
        self.client.post('/acc/deposit', data={
            'card_number': CARD_NUMBER,
            'exp_year': EXP_YEAR,
            'exp_month': EXP_MONTH,
            'cvc': CVC,
            'amount': amount
        }, headers=headers)

    def set_limit(self, username, password, amount, child_email):
        headers = self.generate_auth_header(
            username, password
        )
        self.client.put('/acc/daily-limit-for', data={
            'child_email': child_email,
            'daily_limit': amount
        }, headers=headers)

    # Tests for auth service
    def test_get_account_unautorized(self, *args):
        response = self.client.get('/acc/')
        self.assertEquals(response.status_code, 401)

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD + 'typo'
        )
        response = self.client.get('/acc/', headers=headers)
        self.assertEquals(response.status_code, 401)

    def test_get_account_nonexistent(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.get('/acc/', headers=headers)
        self.assertEquals(response.status_code, 404)

    def test_get_account(self, *args):
        self.create_account(BOB_USERNAME, BOB_PASSWORD)

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )

        response = self.client.get('/acc/', headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)

        self.assertEquals(float(result['daily_limit']), 0.0)
        self.assertEquals(float(result['balance']), 0.0)
        self.assertEquals(result['title'], BOB_EMAIL)

    def test_create_account(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/acc/', headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 201)

        self.assertEquals(float(result['daily_limit']), 0.0)
        self.assertEquals(float(result['balance']), 0.0)
        self.assertEquals(result['title'], BOB_EMAIL)

    def test_get_daily_limit_not_parent(self, *args):
        self.create_account(CAREN_USERNAME, CAREN_PASSWORD)

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.get('/acc/daily-limit-for', data={
            'child_email': CAREN_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.get('/acc/daily-limit-for', data={
            'child_email': CAREN_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

    def test_get_daily_limit_nonexistent(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.get('/acc/daily-limit-for', data={
            'child_email': BOB_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 404)

    def test_get_daily_limit(self, *args):
        self.create_account(BOB_USERNAME, BOB_PASSWORD)

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.get('/acc/daily-limit-for', data={
            'child_email': BOB_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(float(result['daily_limit']), 0.0)

    def test_put_daily_limit_not_parent(self, *args):
        self.create_account(CAREN_USERNAME, CAREN_PASSWORD)

        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.put('/acc/daily-limit-for', data={
            'child_email': CAREN_EMAIL,
            'daily_limit': DAILY_LIMIT
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.put('/acc/daily-limit-for', data={
            'child_email': CAREN_EMAIL,
            'daily_limit': DAILY_LIMIT
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

    def test_put_daily_limit(self, *args):
        self.create_account(BOB_USERNAME, BOB_PASSWORD)

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.put('/acc/daily-limit-for', data={
            'child_email': BOB_EMAIL,
            'daily_limit': DAILY_LIMIT
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['daily_limit'], 50.0)

    def test_deposit_card_expired(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.post('/acc/deposit', data={
            'card_number': CARD_NUMBER,
            'exp_year': EXP_YEAR_WRONG,
            'exp_month': EXP_MONTH,
            'cvc': CVC,
            'amount': 150
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertTrue('Card is expired' in result['message'])

    def test_deposit(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.post('/acc/deposit', data={
            'card_number': CARD_NUMBER,
            'exp_year': EXP_YEAR,
            'exp_month': EXP_MONTH,
            'cvc': CVC,
            'amount': 150
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['deposited'], 150)

        trns = Transaction.query.first()
        dep_acc = Account.query.filter(Account.title==DEPOSIT_ACCOUNT).first()
        alice_acc = Account.query.filter(Account.title==ALICE_EMAIL).first()

        self.assertEquals(trns.amount, 150)
        self.assertEquals(trns.credit, dep_acc)
        self.assertEquals(trns.debit, alice_acc)
        self.assertEquals(dep_acc.balance, -150)
        self.assertEquals(alice_acc.balance, 150)

    def test_send_by_student(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/acc/send-money-to', data={
            'child_email': CAREN_EMAIL,
            'amount': 150
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

    def test_send_not_parent(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.post('/acc/send-money-to', data={
            'child_email': CAREN_EMAIL,
            'amount': 150
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

    def test_send_no_funds(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.post('/acc/send-money-to', data={
            'child_email': BOB_EMAIL,
            'amount': 1
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertTrue('insufficient funds' in result['message'])

    def test_send(self, *args):
        self.deposit(ALICE_USERNAME, ALICE_PASSWORD, 150)

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.post('/acc/send-money-to', data={
            'child_email': BOB_EMAIL,
            'amount': 60
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['sent'], 60)

        alice_acc = Account.query.filter(Account.title==ALICE_EMAIL).first()
        bob_acc = Account.query.filter(Account.title==BOB_EMAIL).first()
        trns = Transaction.query.filter(Transaction.credit==alice_acc).first()

        self.assertEquals(trns.amount, 60)
        self.assertEquals(trns.credit, alice_acc)
        self.assertEquals(trns.debit, bob_acc)
        self.assertEquals(alice_acc.balance, 90)
        self.assertEquals(bob_acc.balance, 60)

    def test_spend_by_parent(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.post('/acc/spend', data={
            'memo': 'some spend',
            'amount': 1
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only students' in result['message'])

    def test_spend_no_memo(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/acc/spend', data={
            'memo': '',
            'amount': 1
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertTrue('description' in result['message'])

    def test_spend_no_funds(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/acc/spend', data={
            'memo': 'some spend',
            'amount': 1
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertTrue('insufficient funds' in result['message'])

    def test_spend_limit_exceed(self, *args):
        self.deposit(BOB_USERNAME, BOB_PASSWORD, 150)
        self.set_limit(ALICE_USERNAME, ALICE_PASSWORD, 50, BOB_EMAIL)
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/acc/spend', data={
            'memo': 'some spend',
            'amount': 60
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 400)
        self.assertTrue('exceed daily spent' in result['message'])

    def test_spend(self, *args):
        self.deposit(BOB_USERNAME, BOB_PASSWORD, 150)
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.post('/acc/spend', data={
            'memo': 'some spend',
            'amount': 60
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['spent'], 60)

        spend_acc = Account.query.filter(
            Account.title==SPENDING_ACCOUNT).first()
        bob_acc = Account.query.filter(Account.title==BOB_EMAIL).first()
        trns = Transaction.query.filter(Transaction.credit==bob_acc).first()

        self.assertEquals(trns.amount, 60)
        self.assertEquals(trns.credit, bob_acc)
        self.assertEquals(trns.debit, spend_acc)
        self.assertEquals(bob_acc.balance, 90)
        self.assertEquals(spend_acc.balance, 60)

    def test_transactions(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.get('/acc/transactions', headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(float(result['balanceStart']), 0)
        self.assertEquals(result['transactions'], list())

        self.deposit(BOB_USERNAME, BOB_PASSWORD, 150)

        response = self.client.get('/acc/transactions', headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(float(result['balanceStart']), 0)
        self.assertEquals(len(result['transactions']), 1)

    def test_transactions_for_not_parent(self, *args):
        headers = self.generate_auth_header(
            BOB_USERNAME, BOB_PASSWORD
        )
        response = self.client.get('/acc/transactions-for', data={
            'child_email': CAREN_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.get('/acc/transactions-for', data={
            'child_email': CAREN_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 403)
        self.assertTrue('Only parents' in result['message'])

    def test_transactions_for(self, *args):
        headers = self.generate_auth_header(
            ALICE_USERNAME, ALICE_PASSWORD
        )
        response = self.client.get('/acc/transactions-for', data={
            'child_email': BOB_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(float(result['balanceStart']), 0)
        self.assertEquals(result['transactions'], list())

        self.deposit(BOB_USERNAME, BOB_PASSWORD, 150)

        response = self.client.get('/acc/transactions-for', data={
            'child_email': BOB_EMAIL
        }, headers=headers)
        result = response.json

        self.assertEquals(response.status_code, 200)
        self.assertEquals(float(result['balanceStart']), 0)
        self.assertEquals(len(result['transactions']), 1)


if __name__ == '__main__':
    unittest.main()
