#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
from flask import render_template, request, Response, abort, jsonify

from app import app


CHUNK_SIZE = 1024
API_METHODS = ['GET', 'POST', 'PUT', 'DELETE']


@app.route('/')
def home():
    return render_template("base.html")


@app.route('/api/v1/auth/', methods=API_METHODS)
@app.route('/api/v1/auth/<path:path>', methods=API_METHODS)
def auth_api_gateway(path=''):
    url =  app.config['AUTH_SERVICE_URL'] % path

    return proxy_request(url, 'auth')


@app.route('/api/v1/acc/', methods=API_METHODS)
@app.route('/api/v1/acc/<path:path>', methods=API_METHODS)
def accounts_api_gateway(path=''):
    url =  app.config['ACCOUNTS_SERVICE_URL'] % path

    return proxy_request(url, 'accounts')


def proxy_request(url, service):
    try:
        response = requests.request(
            method=request.method,
            url=url,
            data=request.data,
            params=request.args,
            headers=request.headers
        )
    except requests.ConnectionError:
        return jsonify({'message': '%s service inaccessible' % service}), 502

    def generate():
        for chunk in response.iter_content(CHUNK_SIZE):
            yield chunk

    return Response(generate(), headers = dict(response.headers),
        status=response.status_code)
