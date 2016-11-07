"use strict";

var AUTH_SERVICE_URL = '/api/v1/auth/';

function homeModel(base) {
  var self = this;
  self.base = base;
};

function accountModel(base) {
  var self = this;
  self.base = base;
};

function loginModel(base) {
  var self = this;
  self.base = base;
  self.username = ko.observable('');
  self.password = ko.observable('');
  self.ajaxError = ko.observable('');

  self.login = function() {
    self.ajaxError('');
    $.ajax ({
      type: "GET", url: AUTH_SERVICE_URL,
      username: self.username(), password: self.password(),
      success: function (data) {
        self.base.authenticated(true);
        self.base.username(self.username());
        self.base.password(self.password());
        self.username('');
        self.password('');
        self.base.selectedView(self.base.accountV());
      },
      error: function (e) {
        self.ajaxError(e.status_text);
        if (e.status === 401) {
            self.ajaxError('Wrong username or password');
        } else if (e.status === 502) {
            self.ajaxError('Auth service inaccessible');
        } else {
            self.ajaxError(e.statusText);
        }
      }
    });
  }
};

function logoutModel(base) {
  var self = this;
  self.base = base;
  self.logout = function () {
    self.base.authenticated(false);
    self.base.username('');
    self.base.password('');
    self.base.selectedView(self.base.loginV());
  }
};

function registerStudentModel(base) {
  var self = this;
  self.base = base;
  self.name = ko.observable('');
  self.username = ko.observable('');
  self.email = ko.observable('');
  self.dob = ko.observable('2001-01-01');
  self.shu_id = ko.observable('');
  self.password = ko.observable('');
  self.confirmPassword = ko.observable('');
  self.ajaxError = ko.observable('');
  self.registered = ko.observable(false);

  self.hasError = ko.computed(function() {
    return self.password() !== self.confirmPassword();
  });

  self.register = function() {
    self.ajaxError('');
    var data = {
      name: self.name(),
      username: self.username(),
      email: self.email(),
      dob: self.dob(),
      shu_id: self.shu_id(),
      password: self.password(),
    };
    $.ajax ({
      type: 'POST', url: AUTH_SERVICE_URL + 'register-student',
      contentType: 'application/json; charset=utf-8',
      dataType: "json",
      data: JSON.stringify(data),
      success: function (data) {
        self.registered(true);
        self.name('');
        self.username('');
        self.email('');
        self.dob('2001-01-01');
        self.shu_id('');
        self.password('');
        self.confirmPassword('');
      },
      error: function (e) {
        self.ajaxError(e.status_text);
        if (e.status === 502) {
            self.ajaxError('Auth service inaccessible');
        } else if (e.status === 400) {
            var msg = e.responseJSON.message;
            self.ajaxError(msg[Object.keys(msg)[0]]);
        } else {
            self.ajaxError(e.statusText);
        }
      }
    });
  }
  self.goLogin = function() {
    self.base.selectedView(self.base.loginV());
    self.registered(false);
  }
};

function registerParentModel(base) {
  var self = this;
  self.base = base;
};

function forgetPasswordModel(base) {
  var self = this;
  self.base = base;
};

var View = function(href, title, templateName, data) {
  this.title = title;
  this.href = href;
  this.templateName = templateName;
  this.data = data;
};

function viewModel() {
  var self = this;
  self.authenticated = ko.observable(false);
  self.username = ko.observable('');
  self.password = ko.observable('');

  self.homeV = ko.observable(
    new View("#", "Home", "homeT", new homeModel(self))
  );

  self.accountV = ko.observable(
    new View("#account", "Account", "accountT", new accountModel(self))
  );

  self.loginV = ko.observable(
    new View("#login", "Login", "loginT", new loginModel(self))
  );

  self.logoutV = ko.observable(
    new View("#logout", "Logout", "logoutT", new logoutModel(self))
  );

  self.registerStudentV = ko.observable(
    new View("#register-student", "Register Student", "registerStudentT",
      new registerStudentModel(self))
  );

  self.registerParentV = ko.observable(
    new View("#register-parent", "Register Parent", "registerParentT",
      new registerParentModel(self))
  );

  self.forgetPasswordV = ko.observable(
    new View("#forget-password", "Forget Password", "forgetPasswordT",
      new forgetPasswordModel(self))
  );

  self.selectedView = ko.observable(self.registerStudentV());

  self.viewSelected = ko.computed(function () {
    if (self.selectedView()) {
      location.hash = self.selectedView().href;
    }
  });

};

ko.applyBindings(new viewModel());
