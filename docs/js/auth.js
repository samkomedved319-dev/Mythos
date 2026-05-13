/* ============================================================
   Mythos: Sovereign Architect — Client-Side Auth
   Uses localStorage; token-based flow for CLI integration.
   First account (samkomedved319@gmail.com) = Admin.
   ============================================================ */

(function () {
  'use strict';

  const STORAGE_KEYS = {
    users:   'mythos_users',
    session: 'mythos_session',
  };

  const ADMIN_EMAIL = 'samkomedved319@gmail.com';

  // ---------- Helpers ----------

  function getUsers() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.users)) || {};
    } catch {
      return {};
    }
  }

  function saveUsers(users) {
    localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(users));
  }

  function getSession() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.session)) || null;
    } catch {
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
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    const segments = [];
    for (let s = 0; s < 4; s++) {
      let seg = '';
      for (let i = 0; i < 8; i++) {
        seg += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      segments.push(seg);
    }
    return 'mth_' + segments.join('-');
  }

  function getCurrentUser() {
    const session = getSession();
    if (!session || !session.email) return null;
    const users = getUsers();
    return users[session.email] || null;
  }

  function isAdminEmail(email) {
    return email && email.toLowerCase() === ADMIN_EMAIL;
  }

  /** Determine role: 'admin' if first-ever account is admin email, else 'user' */
  function determineRole(email) {
    const users = getUsers();
    const userCount = Object.keys(users).length;
    // If this is the first account AND it matches admin email → admin
    if (userCount === 0 && isAdminEmail(email)) {
      return 'admin';
    }
    // If the user already has a stored role, preserve it
    if (users[email] && users[email].role) {
      return users[email].role;
    }
    return 'user';
  }

  // ---------- DOM Ready ----------

  document.addEventListener('DOMContentLoaded', function () {
    // Update navbar based on auth state
    const navRight = document.getElementById('nav-right');
    if (navRight) {
      const user = getCurrentUser();
      if (user) {
        const badge = user.role === 'admin' ? '👑 Admin' : '';
        navRight.innerHTML = `
          <a href="dashboard.html">Dashboard</a>
          ${badge ? '<span style="font-size:0.8rem;color:var(--warning);font-family:var(--font-mono);">' + badge + '</span>' : ''}
          <a href="#" id="nav-logout" style="color: var(--text-muted);">Logout</a>
        `;
        const logoutLink = document.getElementById('nav-logout');
        if (logoutLink) {
          logoutLink.addEventListener('click', function (e) {
            e.preventDefault();
            clearSession();
            window.location.href = 'index.html';
          });
        }
      } else {
        navRight.innerHTML = `
          <a href="login.html">Login</a>
          <a href="signup.html" class="btn btn-primary btn-sm">Sign Up</a>
        `;
      }
    }

    // Page-specific init
    const page = document.body.dataset.page;

    if (page === 'signup')    initSignup();
    if (page === 'login')     initLogin();
    if (page === 'dashboard') initDashboard();
    if (page === 'home')      initHome();
  });

  // ---------- Home ----------

  function initHome() {
    const user = getCurrentUser();
    const cta = document.getElementById('hero-cta');
    if (cta && user) {
      cta.innerHTML = `
        <a href="dashboard.html" class="btn btn-primary">Go to Dashboard</a>
      `;
    }
  }

  // ---------- Signup ----------

  function initSignup() {
    const form = document.getElementById('signup-form');
    if (!form) return;

    // Redirect if already logged in
    if (getCurrentUser()) {
      window.location.href = 'dashboard.html';
      return;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const name     = document.getElementById('signup-name').value.trim();
      const email    = document.getElementById('signup-email').value.trim().toLowerCase();
      const password = document.getElementById('signup-password').value;
      const confirm  = document.getElementById('signup-confirm').value;

      // Reset errors
      document.querySelectorAll('.form-error').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));

      let valid = true;

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

      const users = getUsers();

      if (users[email]) {
        showError('signup-email', 'An account with this email already exists');
        return;
      }

      // Determine role: first account to register with admin email becomes admin
      const role = determineRole(email);

      // Create user
      const token = generateToken();
      users[email] = {
        name: name,
        email: email,
        password: btoa(password), // simple obfuscation (static site, no real backend)
        token: token,
        role: role,
        createdAt: new Date().toISOString(),
      };
      saveUsers(users);

      // Auto-login
      setSession({ email: email, name: name, token: token, role: role });

      // Show success message with role info
      const successEl = document.getElementById('signup-success');
      if (successEl) {
        const roleMsg = role === 'admin'
          ? '👑 Admin account created! You are the owner of Mythos.'
          : 'Account created!';
        successEl.textContent = roleMsg + ' Redirecting to dashboard...';
        successEl.classList.add('show');
      }

      setTimeout(function () {
        window.location.href = 'dashboard.html';
      }, 1500);
    });
  }

  // ---------- Login ----------

  function initLogin() {
    const form = document.getElementById('login-form');
    if (!form) return;

    // Redirect if already logged in
    if (getCurrentUser()) {
      window.location.href = 'dashboard.html';
      return;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      const email    = document.getElementById('login-email').value.trim().toLowerCase();
      const password = document.getElementById('login-password').value;

      // Reset errors
      document.querySelectorAll('.form-error').forEach(el => el.style.display = 'none');
      document.querySelectorAll('.form-input').forEach(el => el.classList.remove('error'));
      const alertEl = document.getElementById('login-alert');
      if (alertEl) alertEl.classList.add('hidden');

      let valid = true;

      if (!email) {
        showError('login-email', 'Please enter your email');
        valid = false;
      }
      if (!password) {
        showError('login-password', 'Please enter your password');
        valid = false;
      }
      if (!valid) return;

      const users = getUsers();
      const user = users[email];

      if (!user || user.password !== btoa(password)) {
        if (alertEl) {
          alertEl.textContent = 'Invalid email or password.';
          alertEl.classList.remove('hidden');
        }
        return;
      }

      // Login success
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
    const user = getCurrentUser();
    if (!user) {
      window.location.href = 'login.html';
      return;
    }

    const isAdmin = user.role === 'admin';

    // Display user name
    const nameEl = document.getElementById('dashboard-name');
    if (nameEl) nameEl.textContent = user.name;

    // Display email
    const emailEl = document.getElementById('dashboard-email');
    if (emailEl) emailEl.textContent = user.email;

    // Display role badge
    const roleBadge = document.getElementById('dashboard-role');
    if (roleBadge) {
      if (isAdmin) {
        roleBadge.innerHTML = '👑 Admin / Owner';
        roleBadge.style.color = 'var(--warning)';
      } else {
        roleBadge.textContent = 'User';
        roleBadge.style.color = 'var(--text-secondary)';
      }
    }

    // Display token
    const tokenEl = document.getElementById('dashboard-token');
    if (tokenEl) tokenEl.textContent = user.token;

    // Show/hide admin panel
    const adminPanel = document.getElementById('admin-panel');
    if (adminPanel) {
      if (isAdmin) {
        adminPanel.classList.remove('hidden');
        // Populate admin info
        const users = getUsers();
        const totalUsers = Object.keys(users).length;
        const adminUserCount = document.getElementById('admin-user-count');
        if (adminUserCount) adminUserCount.textContent = totalUsers;
        const adminEmailShow = document.getElementById('admin-email-show');
        if (adminEmailShow) adminEmailShow.textContent = user.email;
      } else {
        adminPanel.classList.add('hidden');
      }
    }

    // Copy token button
    const copyBtn = document.getElementById('token-copy');
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
            const range = document.createRange();
            range.selectNodeContents(tokenEl);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
          }
        });
      });
    }

    // Copy setup command
    const setupCopyBtn = document.getElementById('setup-copy');
    if (setupCopyBtn) {
      setupCopyBtn.addEventListener('click', function () {
        const setupCmd =
`# Run this in your terminal to authenticate Mythos:
python mythos_cli.py

# When prompted, enter:
#   Email: ${user.email}
#   Token: ${user.token}`;
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
    const logoutBtn = document.getElementById('dashboard-logout');
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
    const input = document.getElementById(inputId);
    if (input) {
      input.classList.add('error');
      const errorEl = input.parentElement.querySelector('.form-error');
      if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
      }
    }
  }

})();
