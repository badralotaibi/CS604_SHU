Get balance code:

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

---------------------------------------------------------------
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

--------------------------------------------
Unit test:

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

----
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
