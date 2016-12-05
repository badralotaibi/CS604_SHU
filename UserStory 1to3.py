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

    --------
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
-------
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


---------
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
-----------------------------------------------------
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
