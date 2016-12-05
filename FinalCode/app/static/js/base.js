"use strict";

var AUTH_SERVICE_URL = '/api/v1/auth/';
var ACCOUNTS_SERVICE_URL = '/api/v1/acc/';

function View(href, title, templateName, data) {
  this.title = title;
  this.href = href;
  this.templateName = templateName;
  this.data = data;
}

function processError(e, observable) {
  if (e.responseJSON !== undefined) {
    var msg = e.responseJSON.message;
    if (typeof msg === "string") {
      observable(msg);
    } else {
      var key = Object.keys(msg)[0];
      observable(msg[key]);
    }
  } else {
    observable(e.statusText);
  }
}

function viewModel() {
  var self = this;
  self.auth = ko.observable(null);

  self.homeV = ko.observable(
    new View("/", "Home", "homeT", new homeModel(self))
  );

  self.adminV = ko.observable(
    new View("/#admin", "Admin", "adminT", new adminModel(self))
  );

  self.accountV = ko.observable(
    new View("/#account", "Account", "accountT", new accountModel(self))
  );

  self.loginV = ko.observable(
    new View("/#login", "Login", "loginT", new loginModel(self))
  );

  self.sessionExpiredV = ko.observable(
    new View("/#session-expired", "Session Expired", "sessionExpiredT",
      new sessionExpiredModel(self))
  );

  self.logoutV = ko.observable(
    new View("/#logout", "Logout", "logoutT", new logoutModel(self))
  );

  self.registerStudentV = ko.observable(
    new View("/#register-student", "Register Student", "registerStudentT",
      new registerStudentModel(self))
  );

  self.registerParentV = ko.observable(
    new View("/#register-parent", "Register Parent", "registerParentT",
      new registerParentModel(self))
  );

  self.forgetPasswordV = ko.observable(
    new View("/#forget-password", "Forget Password", "forgetPasswordT",
      new forgetPasswordModel(self))
  );

  self.resetPasswordV = ko.observable(
    new View("/#reset-password-:token", "Reset Password", "resetPasswordT",
      new resetPasswordModel(self))
  );

  self.approveParentV = ko.observable(
    new View("/#approve-parent-:token", "Approve Parent", "approveParentT",
      new approveParentModel(self))
  );

  self.selectedView = ko.observable();

  self.selectedView.subscribe(function(previousView) {
    if (previousView !== undefined) {
      self.previousView = previousView;
      if(previousView.data.hideModals !== undefined) {
        previousView.data.hideModals();
      }
    }
  }, null, "beforeChange");

  self.selectedView.subscribe(function(nextView) {
    if (self.previousView !== undefined
    && self.previousView.data.leave !== undefined
    && self.previousView !== nextView) {
      self.previousView.data.leave();
    }
  });

  // init session and session timer
  var sessionAuth = sessionStorage.getItem('auth');
  if (sessionAuth !== null) {
    sessionAuth = JSON.parse(sessionStorage.getItem('auth'));
    sessionAuth.expires_at = new Date(sessionAuth.expires_at);
    self.auth(sessionAuth);
  };

  self.sessionExpired = function() {
    self.auth(null);
    sessionStorage.removeItem('auth');
    location = self.sessionExpiredV().href;
  };

  self.sessionTimer = function() {
    if (!self.auth()) {
      return;
    }
    var timeLeft = self.auth().expires_at.getTime() - new Date().getTime();
    if (timeLeft < 10000) {
      var msIdle = (new Date - self.lastActive);
      if (msIdle > 50000 || timeLeft < 5000 ) {
        self.sessionExpired();
      } else {
        $.ajax ({
          type: "POST", url: AUTH_SERVICE_URL,
          username: self.auth().token,
          passowrd: 'x',
          headers: {
            "Authorization": "Basic " +
              btoa(self.auth().token + ":" + 'x')
          },
          success: function (data) {
            var now = new Date();
            data.expires_at = new Date(now.getTime() + data.expires*1000);
            self.auth(data);
            sessionStorage.setItem('auth', JSON.stringify(data));
          },
          error: function (e) {
            self.sessionExpired();
          }
        });
      }
    }
  };

  self.sessionTimerId = setInterval(self.sessionTimer, 1000);

  $(document).on('mousemove', function() {
    if (!self.auth()) {
      return;
    }
    self.lastActive = new Date();
  })

  $(document).on('keypress', function() {
    if (!self.auth()) {
      return;
    }
    self.lastActive = new Date();
  })

  // init routes
  Sammy(function() {
      this.get(self.homeV().href, function() {
        if (!self.auth()) {
          self.selectedView(self.homeV());
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.accountV().href, function() {
        if (!self.auth()) {
          location = self.loginV().href;
        } else if (self.auth().isAdmin) {
          location = self.adminV().href;
        } else {
          self.accountV().data.init();
          self.selectedView(self.accountV());
        }
      });

      this.get(self.adminV().href, function() {
        if (!self.auth()) {
          location = self.loginV().href;
        } else if (!self.auth().isAdmin) {
          location = self.accountV().href;
        } else {
          self.adminV().data.init();
          self.selectedView(self.adminV());
        }
      });

      this.get(self.loginV().href, function() {
        var token = this.params.token;
        if (!self.auth()) {
          self.selectedView(self.loginV());
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.sessionExpiredV().href, function() {
        if (!self.auth()) {
          self.selectedView(self.sessionExpiredV());
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.logoutV().href, function() {
        if (!self.auth()) {
          location = self.homeV().href;
        } else {
          self.selectedView(self.logoutV());
        }
      });

      this.get(self.registerStudentV().href, function() {
        if (!self.auth()) {
          self.selectedView(self.registerStudentV());
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.registerParentV().href, function() {
        if (!self.auth()) {
          self.selectedView(self.registerParentV());
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.forgetPasswordV().href, function() {
        if (!self.auth()) {
          self.selectedView(self.forgetPasswordV());
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.resetPasswordV().href, function() {
        if (!self.auth()) {
          var token = this.params.token;
          var view = self.resetPasswordV();
          view.data.token(token);
          self.selectedView(view);
        } else {
          location = self.accountV().href;
        }
      });

      this.get(self.approveParentV().href, function() {
        if (!self.auth()) {
          var view = self.loginV();
          view.data.nextUrl(location.hash);
          location = self.loginV().href;
        } else {
          var token = this.params.token;
          var view = self.approveParentV();
          view.data.token(token);
          view.data.init();
          self.selectedView(view);
        }
      });

      this._checkFormSubmission = function(form) {
        return false;
      };
  }).run();
}

ko.applyBindings(new viewModel());
