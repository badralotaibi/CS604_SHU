#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
import json
import pytz
import requests
import requests.auth
from flask_restful import (Resource, reqparse, Api, abort, inputs, fields,
    marshal)
from flask_httpauth import HTTPBasicAuth
from flask import g, jsonify
from sqlalchemy.sql import func

from . import app, db
from .models import Account, Transaction
from .validators import (card_number, exp_year, exp_month, cvc,
    positive_amount, limit_amount)


api = Api(app)
auth = HTTPBasicAuth()
tz = app.config['TZ']


def check_parent_for(child_email):
    try:
        response = requests.get(
            url=app.config['AUTH_SERVICE_URL'] + 'check-parent-for',
            headers={'content-type': 'application/json'},
            data=json.dumps({'child_email': child_email}),
            auth=requests.auth.HTTPBasicAuth(g.auth_data['token'], 'x')
        )
        response = response.json()
    except requests.ConnectionError:
        abort(502)

    return response


@auth.verify_password
def verify_password(username, password):
    try:
        response = requests.post(
            url=app.config['AUTH_SERVICE_URL'],
            auth=requests.auth.HTTPBasicAuth(username, password)
        )
    except requests.ConnectionError:
        return False

    if response.status_code != 200:
        return False

    try:
        auth_data = response.json()
    except:
        return False

    if type(auth_data) != dict or not 'email' in auth_data:
        return False

    g.auth_data = auth_data
    return True


class Money(fields.Float):
    def format(self, val):
        val = '%.2f' % val
        return val


account_fields = {
    'title': fields.String,
    'balance': Money,
    'daily_limit': Money
}


transactions_fields = {
    'balanceStart': fields.String,
    'transactions': fields.List(fields.Nested({
      'created': fields.DateTime(dt_format='iso8601'),
      'account': fields.String,
      'memo': fields.String,
      'debit': fields.String,
      'credit': fields.String,
      'balance': fields.String,
    }))
}


class AccountResource(Resource):
    @auth.login_required
    def get(self):
        account = Account.query.filter_by(title=g.auth_data['email']).first()

        if not account:
            abort(404)

        return marshal(account, account_fields)

    @auth.login_required
    def post(self):
        email = g.auth_data['email']
        account = Account.query.filter_by(title=email).first()

        if not account:
            account = Account(title=email)
            db.session.add(account)
            db.session.commit()
            result_code = 201
        else:
            result_code = 200

        return marshal(account, account_fields), result_code


class DailyLimitFor(Resource):
    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('child_email', type=str, required=True,
            nullable=False)
        parser.add_argument('_', type=str, dest='nocache')
        args = parser.parse_args(strict=True)

        check_parent = check_parent_for(args.child_email)

        if not 'isParent' in check_parent or not check_parent['isParent']:
            return {'message': 'Only parents can call this'}, 403

        account = Account.query.filter_by(title=args.child_email).first()

        if not account:
            abort(404)

        return jsonify({
          'daily_limit': '%.2f' % account.daily_limit
        })

    @auth.login_required
    def put(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('child_email', type=str, required=True,
            nullable=False)
        parser.add_argument('daily_limit', type=limit_amount,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        check_parent = check_parent_for(args.child_email)

        if not 'isParent' in check_parent or not check_parent['isParent']:
            return {'message': 'Only parents can call this'}, 403

        account = Account.query.filter_by(title=args.child_email).first()

        if not account:
            account = Account(title=args.child_email)
        account.daily_limit = args.daily_limit
        db.session.add(account)
        db.session.commit()

        return jsonify({
          'daily_limit': account.daily_limit
        })


class Deposit(Resource):
    @auth.login_required
    def post(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('card_number', type=card_number, required=True,
            nullable=False)
        parser.add_argument('exp_year', type=exp_year, required=True,
            nullable=False)
        parser.add_argument('exp_month', type=exp_month, required=True,
            nullable=False)
        parser.add_argument('cvc', type=cvc, required=True,
            nullable=False)
        parser.add_argument('amount', type=positive_amount,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        exp_date = date(
            year=(int('20%d' % args.exp_year)),
            month=args.exp_month,
            day=1
        )

        today = date.today()

        exp_seconds = (today-exp_date).total_seconds()

        if exp_seconds >= 0:
            return {'message': 'Card is expired'}, 400

        credit_acc = Account.query.filter_by(
            title=app.config['DEPOSIT_ACCOUNT']
        ).first()

        if not credit_acc:
            credit_acc = Account(title=app.config['DEPOSIT_ACCOUNT'])
            db.session.add(credit_acc)
            db.session.commit()

        email = g.auth_data['email']
        debit_acc = Account.query.filter_by(title=email).first()

        if not debit_acc:
            debit_acc = Account(title=email)
            db.session.add(debit_acc)
            db.session.commit()

        trns = Transaction(
            amount=args.amount,
            debit_id=debit_acc.id,
            credit_id=credit_acc.id,
            memo=('Deposit from card number %s, expires %s/%s, cvc %s' % (
              args.card_number,
              args.exp_month,
              args.exp_year,
              args.cvc
            ))
        )

        credit_acc.balance -= args.amount
        debit_acc.balance += args.amount

        db.session.add(trns)
        db.session.add(credit_acc)
        db.session.add(debit_acc)

        db.session.commit()

        return jsonify({'deposited': trns.amount})


class SendMoneyTo(Resource):
    @auth.login_required
    def post(self):
        if not g.auth_data['isParent']:
            return {'message': 'Only parents can send money'}, 403

        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('child_email', type=str, required=True,
            nullable=False)
        parser.add_argument('amount', type=positive_amount,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        check_parent = check_parent_for(args.child_email)

        if not 'isParent' in check_parent or not check_parent['isParent']:
            return {'message': 'Only parents can send money'}, 403

        email = g.auth_data['email']
        credit_acc = Account.query.filter_by(title=email).first()
        if not credit_acc or credit_acc.balance < args.amount:
            return {'message': 'You have insufficient funds to send'}, 400

        debit_acc = Account.query.filter_by(title=args.child_email).first()
        if not debit_acc:
            debit_acc = Account(title=args.child_email)
            db.session.add(debit_acc)
            db.session.commit()

        trns = Transaction(
            amount=args.amount,
            debit_id=debit_acc.id,
            credit_id=credit_acc.id,
            memo=('Sent for %s' % args.child_email)
        )

        credit_acc.balance -= args.amount
        debit_acc.balance += args.amount

        db.session.add(trns)
        db.session.add(credit_acc)
        db.session.add(debit_acc)

        db.session.commit()

        return jsonify({'sent': trns.amount})


class Spend(Resource):
    @auth.login_required
    def post(self):
        if not g.auth_data['isStudent']:
            return {'message': 'Only students can spend'}, 403

        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('memo', type=str, required=True,
            nullable=False)
        parser.add_argument('amount', type=positive_amount,
            required=True, nullable=False)
        args = parser.parse_args(strict=True)

        if not len(args.memo):
            return {'message': 'You need write spend description'}, 400

        email = g.auth_data['email']
        credit_acc = Account.query.filter_by(title=email).first()

        if not credit_acc or credit_acc.balance < args.amount:
            return {'message': 'You have insufficient funds to spend'}, 400

        if (credit_acc.daily_limit > 0 and
          credit_acc.spent_today() + args.amount > credit_acc.daily_limit):
            return {'message': 'You have exceed daily spent limit'}, 400

        debit_acc = Account.query.filter_by(
            title=app.config['SPENDING_ACCOUNT']
        ).first()

        if not debit_acc:
            debit_acc = Account(title=app.config['SPENDING_ACCOUNT'])
            db.session.add(debit_acc)
            db.session.commit()

        trns = Transaction(
            amount=args.amount,
            debit_id=debit_acc.id,
            credit_id=credit_acc.id,
            memo=args.memo
        )

        credit_acc.balance -= args.amount
        debit_acc.balance += args.amount

        db.session.add(trns)
        db.session.add(credit_acc)
        db.session.add(debit_acc)

        db.session.commit()

        return jsonify({'spent': trns.amount})


class Transactions(Resource):
    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('date_start', type=inputs.date)
        parser.add_argument('date_end', type=inputs.date)
        parser.add_argument('_', type=str, dest='nocache')
        args = parser.parse_args(strict=True)

        email = g.auth_data['email']
        acc = Account.query.filter_by(title=email).first()

        return get_transactions(args.date_start, args.date_end, acc)


class TransactionsFor(Resource):
    @auth.login_required
    def get(self):
        parser = reqparse.RequestParser(trim=True)
        parser.add_argument('date_start', type=inputs.date)
        parser.add_argument('date_end', type=inputs.date)
        parser.add_argument('child_email', type=str, required=True,
            nullable=False)
        parser.add_argument('_', type=str, dest='nocache')
        args = parser.parse_args(strict=True)

        check_parent = check_parent_for(args.child_email)

        if not 'isParent' in check_parent or not check_parent['isParent']:
            return {'message': 'Only parents can call this'}, 403

        acc = Account.query.filter_by(title=args.child_email).first()

        return get_transactions(args.date_start, args.date_end, acc)


def get_balance(datetime_start_utc, acc):
    debit_amount = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.created < datetime_start_utc,
        Transaction.credit_id == acc.id
    ).scalar()

    credit_amount = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.created < datetime_start_utc,
        Transaction.debit_id == acc.id
    ).scalar()

    if debit_amount is None:
        debit_amount = 0.0

    if credit_amount is None:
        credit_amount = 0.0

    return (credit_amount-debit_amount)


def get_transactions(date_start, date_end, acc):
    if date_start is None:
        date_start = date.today()

    if date_end is None:
        date_end = date_start + timedelta(days=1)

    if (date_end-date_start).total_seconds() <= 0:
        return {'message': 'date_end must be greather of date_start'}, 400

    if not acc:
        return jsonify({
            'transactions': [],
            'balanceStart': '%.2f' % 0.0
        })

    datetime_start = tz.localize(datetime(
      date_start.year, date_start.month, date_start.day)
    )
    datetime_start_utc = datetime_start.astimezone(pytz.utc)

    datetime_end = tz.localize(datetime(
      date_end.year, date_end.month, date_end.day)
    )
    datetime_end_utc = datetime_end.astimezone(pytz.utc)

    balance_start = get_balance(datetime_start_utc, acc)

    trns = Transaction.query.filter(
        Transaction.created >= datetime_start_utc,
        Transaction.created < datetime_end_utc,
        db.or_(Transaction.credit_id == acc.id,
        Transaction.debit_id == acc.id)
    ).order_by(Transaction.created.asc()).all()

    balance = balance_start
    result = list()
    for t in trns:
        if t.credit == acc:
            account = t.debit.title
            debit = '%.2f' % t.amount
            credit = ''
            balance -= t.amount
        else:
            account = t.credit.title
            debit = ''
            credit = '%.2f' % t.amount
            balance += t.amount

        result.append({
            'created': pytz.utc.localize(t.created),
            'account': account,
            'memo': t.memo,
            'debit': debit,
            'credit': credit,
            'balance': '%.2f' % balance
        })

    return marshal({
        'transactions': result,
        'balanceStart': '%.2f' % balance_start
    }, transactions_fields)


ACCOUNTS_PATH = '/acc/%s'
api.add_resource(AccountResource, ACCOUNTS_PATH % '')
api.add_resource(DailyLimitFor, ACCOUNTS_PATH % 'daily-limit-for')
api.add_resource(Deposit, ACCOUNTS_PATH % 'deposit')
api.add_resource(SendMoneyTo, ACCOUNTS_PATH % 'send-money-to')
api.add_resource(Spend, ACCOUNTS_PATH % 'spend')
api.add_resource(Transactions, ACCOUNTS_PATH % 'transactions')
api.add_resource(TransactionsFor, ACCOUNTS_PATH % 'transactions-for')
