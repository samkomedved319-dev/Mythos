/* ============================================================
   Mythos: Sovereign Architect — Client-Side Auth
   Uses localStorage; token-based flow for CLI integration.
   First account (samkomedved319@gmail.com) = Admin.
   Supports seamless CLI callback via ?cli_port=PORT
   ============================================================ */

(function () {
  'use strict';

  var STORAGE_KEYS = {
    users:   'mythos_users',
    session: 'mythos_session',
  };

  var ADMIN_EMAIL = 'samkomedved319@gmail.com';

  // ---------- Helpers ----------

  function getUsers() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.users)) || {};
    } catch (e) {
      return {};
    }
  }

  function saveUsers(users) {
    localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(users));
  }

  function getSession() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.session)) || null;
    } catch (e) {
      return null;
    }
  }

  function setSession(data) {
    localStorage.setItem(STORAGE_KEYS.session, JSON.stringify(data));
  }

  function clearSession() {
    localStorage.removeItem(STORAGE_KEYS.session);
  }

  function generateToken() {
    var chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    var segments = [];
    for (var s = 0; s < 4; s++) {
      var seg = '';
      for (var i = 0; i < 8; i++) {
        seg += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      segments.push(seg);
    }
    return 'mth_' + segments.join('-');
  }

  function getCurrentUser() {
    var session = getSession();
    if (!session || !session.email) return null;
    var users = getUsers();
    return users[session.email] || null;
  }

  function isAdminEmail(email) {
    return email && email.toLowerCase() === ADMIN_EMAIL;
  }

  function determineRole(email) {
    var users = getUsers();
    var userCount = Object.keys(users).length;
    if (userCount === 0 && isAdminEmail(email)) {
      return 'admin';
    }
    if (users[email] && users[email].role) {
      return users[email].role;
    }
    return 'user';
  }

  /** Get the CLI callback port from sessionStorage (saved from URL param) */
  function getCliPort() {
    return sessionStorage.getItem('mythos_cli_port');
  }

  /** Notify the local CLI server that auth succeeded, then remove the port. */
  function notifyCliServer(email, token, name, role) {
    var port = getCliPort();
    if (!port) return;
    sessionStorage.removeItem('mythos_cli_port');

    var callbackUrl = 'http://localhost:' + port +
      '/auth?email=' + encodeURIComponent(email) +
      '&token=' + encodeURIComponent(token) +
      '&name=' + encodeURIComponent(name || email) +
      '&role=' + encodeURIComponent(role || 'user');

    // Use an image beacon (works across origins, no CORS issues)
    try {
      var img = new Image();
      img.src = callbackUrl;
    } catch (e) {
      // Silently fall back — user will see the dashboard
    }
  }

  // ---------- DOM Ready ----------

  document.addEventListener('DOMContentLoaded', function () {

    // ---- Capture cli_port from URL and store in sessionStorage ----
    var urlParams = new URLSearchParams(window.location.search);
    var cliPort = urlParams.get('cli_port');
    if (cliPort) {
      sessionStorage.setItem('mythos_cli_port', cliPort);
    }

    // ---- Update navbar based on auth state ----
    var navRight = document.getElementById('nav-right');
    if (navRight) {
      var user = getCurrentUser();
      if (user) {
        var badge = user.role === 'admin' ? '👑 Admin' : '';
        navRight.innerHTML =
          '<a href="dashboard.html">Dashboard</a>' +
          (badge ? '<span style="font-size:0.8rem;color:var(--warning);font-family:var(--font-mono);">' + badge + '</span>' : '') +
          '<a href="#" id="nav-logout" style="color: var(--text-muted);">Logout</a>';
        var logoutLink = document.getElementById('nav-logout');
        if (logoutLink) {
          logoutLink.addEventListener('click', function (e) {
            e.preventDefault();
            clearSession();
            window.location.href = 'index.html';
          });
        }
      } else {
        navRight.innerHTML =
          '<a href="login.html">Login</a>' +
          '<a href="signup.html" class="btn btn-primary btn-sm">Sign Up</a>';
      }
    }

    // ---- Page-specific init ----
    var page = document.body.dataset.page;
    if (page === 'signup')    initSignup();
    if (page === 'login')     initLogin();
    if (page === 'dashboard') initDashboard();
    if (page === 'home')      initHome();
  });

  // ---------- Home ----------

  function initHome() {
    var user = getCurrentUser();
    var cta = document.getElementById('hero-cta');
    if (cta && user) {
      cta.innerHTML = '<a href="dashboard.html" class="btn btn-primary">Go to Dashboard</a>';
    }
  }

  // ---------- Signup ----------

  function initSignup() {
    var form = document.getElementById('signup-form');
    if (!form) return;

    if (getCurrentUser()) {
      window.location.href = 'dashboard.html';
      return;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var name     = document.getElementById('signup-name').value.trim();
      var email    = document.getElementById('signup-email').value.trim().toLowerCase();
      var password = document.getElementById('signup-password').value;
      var confirm  = document.getElementById('signup-confirm').value;

      document.querySelectorAll('.form-error').forEach(function (el) { el.style.display = 'none'; });
      document.querySelectorAll('.form-input').forEach(function (el) { el.classList.remove('error'); });

      var valid = true;

      if (!name || name.length < 2) {
        showError('signup-name', 'Name must be at least 2 characters');
        valid = false;
      }
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showError('signup-email', 'Please enter a valid email address');
        valid = false;
      }
      if (!password || password.length < 6) {
        showError('signup-password', 'Password must be at least 6 characters');
        valid = false;
      }
      if (password !== confirm) {
        showError('signup-confirm', 'Passwords do not match');
        valid = false;
      }
      if (!valid) return;

      var users = getUsers();

      if (users[email]) {
        showError('signup-email', 'An account with this email already exists');
        return;
      }

      var role = determineRole(email);
      var token = generateToken();

      users[email] = {
        name: name,
        email: email,
        password: btoa(password),
        token: token,
        role: role,
        createdAt: new Date().toISOString(),
      };
      saveUsers(users);

      setSession({ email: email, name: name, token: token, role: role });

      // ---- Notify local CLI server (if cli_port was set) ----
      notifyCliServer(email, token, name, role);

      var successEl = document.getElementById('signup-success');
      if (successEl) {
        var roleMsg = role === 'admin'
          ? '👑 Admin account created! You are the owner of Mythos.'
          : 'Account created!';
        successEl.textContent = roleMsg + ' Redirecting to dashboard...';
        successEl.classList.add('show');
      }

      setTimeout(function () {
        // If there's a CLI port, the CLI server already got the token.
        // Redirect to dashboard (or back to CLI via the port was already done).
        window.location.href = 'dashboard.html';
      }, 1500);
    });
  }

  // ---------- Login ----------

  function initLogin() {
    var form = document.getElementById('login-form');
    if (!form) return;

    if (getCurrentUser()) {
      window.location.href = 'dashboard.html';
      return;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var email    = document.getElementById('login-email').value.trim().toLowerCase();
      var password = document.getElementById('login-password').value;

      document.querySelectorAll('.form-error').forEach(function (el) { el.style.display = 'none'; });
      document.querySelectorAll('.form-input').forEach(function (el) { el.classList.remove('error'); });
      var alertEl = document.getElementById('login-alert');
      if (alertEl) alertEl.classList.add('hidden');

      var valid = true;
      if (!email) {
        showError('login-email', 'Please enter your email');
        valid = false;
      }
      if (!password) {
        showError('login-password', 'Please enter your password');
        valid = false;
      }
      if (!valid) return;

      var users = getUsers();
      var user = users[email];

      if (!user || user.password !== btoa(password)) {
        if (alertEl) {
          alertEl.textContent = 'Invalid email or password.';
          alertEl.classList.remove('hidden');
        }
        return;
      }

      setSession({
        email: user.email,
        name: user.name,
        token: user.token,
        role: user.role || 'user',
      });

      // ---- Notify local CLI server (if cli_port was set) ----
      notifyCliServer(user.email, user.token, user.name, user.role);

      window.location.href = 'dashboard.html';
    });
  }

  // ---------- Dashboard ----------

  function initDashboard() {
    var user = getCurrentUser();
    if (!user) {
      window.location.href = 'login.html';
      return;
    }

    var isAdmin = user.role === 'admin';

    // Check if we came from a CLI auth callback
    var urlParams = new URLSearchParams(window.location.search);
    var authSuccess = urlParams.get('auth');

    var nameEl = document.getElementById('dashboard-name');
    if (nameEl) nameEl.textContent = user.name;

    var emailEl = document.getElementById('dashboard-email');
    if (emailEl) emailEl.textContent = user.email;

    var roleBadge = document.getElementById('dashboard-role');
    if (roleBadge) {
      if (isAdmin) {
        roleBadge.innerHTML = '👑 Admin / Owner';
        roleBadge.style.color = 'var(--warning)';
      } else {
        roleBadge.textContent = 'User';
        roleBadge.style.color = 'var(--text-secondary)';
      }
    }

    var tokenEl = document.getElementById('dashboard-token');
    if (tokenEl) tokenEl.textContent = user.token;

    // Auth success banner (redirected from CLI callback)
    var authBanner = document.getElementById('auth-success-banner');
    if (authBanner && authSuccess === 'success') {
      authBanner.classList.remove('hidden');
    }

    // Admin panel
    var adminPanel = document.getElementById('admin-panel');
    if (adminPanel) {
      if (isAdmin) {
        adminPanel.classList.remove('hidden');
        var users = getUsers();
        var totalUsers = Object.keys(users).length;
        var adminUserCount = document.getElementById('admin-user-count');
        if (adminUserCount) adminUserCount.textContent = totalUsers;
        var adminEmailShow = document.getElementById('admin-email-show');
        if (adminEmailShow) adminEmailShow.textContent = user.email;
      } else {
        adminPanel.classList.add('hidden');
      }
    }

    // Copy token
    var copyBtn = document.getElementById('token-copy');
    if (copyBtn) {
      copyBtn.addEventListener('click', function () {
        navigator.clipboard.writeText(user.token).then(function () {
          copyBtn.textContent = 'Copied!';
          copyBtn.classList.add('copied');
          setTimeout(function () {
            copyBtn.textContent = 'Copy';
            copyBtn.classList.remove('copied');
          }, 2000);
        }).catch(function () {
          if (tokenEl) {
            var range = document.createRange();
            range.selectNodeContents(tokenEl);
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
          }
        });
      });
    }

    // Copy setup command
    var setupCopyBtn = document.getElementById('setup-copy');
    if (setupCopyBtn) {
      setupCopyBtn.addEventListener('click', function () {
        var setupCmd =
'# Authenticate Mythos CLI:\npython mythos_cli.py\n\n# When prompted, enter:\n#   Email: ' + user.email + '\n#   Token: ' + user.token;
        navigator.clipboard.writeText(setupCmd).then(function () {
          setupCopyBtn.textContent = 'Copied!';
          setupCopyBtn.classList.add('copied');
          setTimeout(function () {
            setupCopyBtn.textContent = 'Copy Setup Command';
            setupCopyBtn.classList.remove('copied');
          }, 2000);
        });
      });
    }

    // Logout
    var logoutBtn = document.getElementById('dashboard-logout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        clearSession();
        window.location.href = 'index.html';
      });
    }
  }

  // ---------- Utilities ----------

  function showError(inputId, message) {
    var input = document.getElementById(inputId);
    if (input) {
      input.classList.add('error');
      var errorEl = input.parentElement.querySelector('.form-error');
      if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
      }
    }
  }

})();
