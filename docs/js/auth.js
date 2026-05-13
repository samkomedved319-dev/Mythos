/* ============================================================
   Mythos: Sovereign Architect — Client-Side Auth
   Uses localStorage for account management.
   First account (samkomedved319@gmail.com) becomes Admin.
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
    // First-ever account with admin email → admin
    if (userCount === 0 && isAdminEmail(email)) {
      return 'admin';
    }
    // Preserve existing role
    if (users[email] && users[email].role) {
      return users[email].role;
    }
    return 'user';
  }

  // ---------- DOM Ready ----------

  document.addEventListener('DOMContentLoaded', function () {

    // ---- Update navbar based on auth state ----
    var navRight = document.getElementById('nav-right');
    if (navRight) {
      var user = getCurrentUser();
      if (user) {
        var badge = '';
        if (user.role === 'admin') {
          badge = '<span style="font-size:0.8rem;color:var(--warning);font-family:var(--font-mono);">👑 Admin</span>';
        }
        navRight.innerHTML =
          '<a href="dashboard.html">Dashboard</a>' +
          badge +
          '<a href="#" id="nav-logout" style="color: var(--text-muted);">Logout</a>';
        var l = document.getElementById('nav-logout');
        if (l) {
          l.addEventListener('click', function (e) {
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

      var successEl = document.getElementById('signup-success');
      if (successEl) {
        var msg = role === 'admin'
          ? '👑 Admin account created! You are the owner of Mythos.'
          : 'Account created!';
        successEl.textContent = msg + ' Redirecting to dashboard...';
        successEl.classList.add('show');
      }

      setTimeout(function () {
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

    document.getElementById('dashboard-name').textContent = user.name;
    document.getElementById('dashboard-email').textContent = user.email;

    var roleEl = document.getElementById('dashboard-role');
    if (roleEl) {
      if (isAdmin) {
        roleEl.innerHTML = '👑 Admin / Owner';
        roleEl.style.color = 'var(--warning)';
      } else {
        roleEl.textContent = 'User';
        roleEl.style.color = 'var(--text-secondary)';
      }
    }

    var tokenEl = document.getElementById('dashboard-token');
    if (tokenEl) tokenEl.textContent = user.token;

    // Admin panel
    var adminPanel = document.getElementById('admin-panel');
    if (adminPanel) {
      if (isAdmin) {
        adminPanel.classList.remove('hidden');
        var users = getUsers();
        var total = Object.keys(users).length;
        var countEl = document.getElementById('admin-user-count');
        if (countEl) countEl.textContent = total;
        var adminEmailEl = document.getElementById('admin-email-show');
        if (adminEmailEl) adminEmailEl.textContent = user.email;
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
    var setupBtn = document.getElementById('setup-copy');
    if (setupBtn) {
      setupBtn.addEventListener('click', function () {
        var cmd =
'# In your terminal, run:\npython mythos_cli.py\n\n# When prompted, enter:\n#   Email: ' + user.email + '\n#   Token: ' + user.token;
        navigator.clipboard.writeText(cmd).then(function () {
          setupBtn.textContent = 'Copied!';
          setupBtn.classList.add('copied');
          setTimeout(function () {
            setupBtn.textContent = 'Copy Setup Command';
            setupBtn.classList.remove('copied');
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
