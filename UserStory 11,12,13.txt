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


-----


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


------
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

------

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


-----------

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

        self.assertEquals(response.status_code, 200)
        self.assertEquals(result['daily_limit'], 50.0)
