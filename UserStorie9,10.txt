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
-------

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
-----

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
-------

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
-------


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
-------
