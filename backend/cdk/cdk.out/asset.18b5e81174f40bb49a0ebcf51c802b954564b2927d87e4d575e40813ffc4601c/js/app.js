/**
 * Auditor Lead — SPA Router y App principal
 * Integrates Cognito auth with route protection.
 */
const App = (() => {
  const appContainer = document.getElementById('app');
  let currentRoute = '';

  // ===== Routes =====
  const routes = {
    '/': { page: LandingPage, nav: 'home', protected: true },
    '/acerca': { page: AcercaPage, nav: 'acerca', protected: false },
    '/auditorias': { page: AuditoriasPage, nav: 'auditorias', protected: true },
    '/evaluaciones': { page: EvaluacionesPage, nav: 'evaluaciones', protected: true },
    '/login': { page: LoginPage, nav: null, protected: false, hideNav: true },
    '/register': { page: RegisterPage, nav: null, protected: false, hideNav: true },
  };

  // ===== Router =====
  function getRoute() {
    const hash = window.location.hash.slice(1) || '/';
    return hash;
  }

  function parseRoute(path) {
    // Audit detail: /auditorias/:id
    const auditoriaMatch = path.match(/^\/auditorias\/(\d+)$/);
    if (auditoriaMatch) {
      return { page: AuditoriaDetallePage, nav: 'auditorias', params: { id: auditoriaMatch[1] }, protected: true };
    }
    return routes[path] || routes['/'];
  }

  async function navigate() {
    const path = getRoute();
    const { page, nav, params, protected: isProtected, hideNav } = parseRoute(path);

    // Auth guard — redirect to login if not authenticated
    if (isProtected && !Auth.isAuthenticated()) {
      window.location.hash = '#/login';
      return;
    }

    // Redirect away from login if already authenticated
    if (path === '/login' && Auth.isAuthenticated()) {
      window.location.hash = '#/';
      return;
    }

    if (path === currentRoute) return;
    currentRoute = path;

    // Show/hide navbar
    const navbar = document.querySelector('.navbar');
    const footer = document.querySelector('.footer');
    if (hideNav) {
      navbar.style.display = 'none';
      footer.style.display = 'none';
    } else {
      navbar.style.display = '';
      footer.style.display = '';
    }

    // Render page
    appContainer.innerHTML = page.render(params ? params.id : null);

    // Update active nav link
    updateNavActive(nav);

    // Run after render logic
    if (page.afterRender) {
      await page.afterRender(params ? params.id : null);
    }

    // Scroll to top
    window.scrollTo(0, 0);
  }

  function updateNavActive(activeNav) {
    document.querySelectorAll('.navbar__link').forEach(link => {
      link.classList.remove('navbar__link--active');
      if (link.dataset.nav === activeNav) {
        link.classList.add('navbar__link--active');
      }
    });
  }

  // ===== Auth state change handler =====
  function onAuthChange(user) {
    const usernameEl = document.querySelector('.navbar__username');
    const logoutBtn = document.getElementById('logout-btn');

    if (user) {
      if (usernameEl) usernameEl.textContent = user.username;
      if (logoutBtn) logoutBtn.style.display = '';
    } else {
      if (usernameEl) usernameEl.textContent = '';
      if (logoutBtn) logoutBtn.style.display = 'none';
    }
  }

  function handleLogout() {
    Auth.signOut();
    currentRoute = '';
    onAuthChange(null);
    window.location.hash = '#/login';
  }

  // ===== Toast notifications =====
  let toastTimeout = null;

  function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('toast--visible'));

    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toast.classList.remove('toast--visible');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // ===== Theme Toggle =====
  function setupThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;

    // Load saved preference
    const saved = localStorage.getItem('theme');
    if (saved) {
      document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }

    toggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
    });
  }

  // ===== Mobile Menu =====
  function setupMobileMenu() {
    const navbar = document.querySelector('.navbar__container');
    const links = document.querySelector('.navbar__links');

    const toggle = document.createElement('button');
    toggle.className = 'navbar__toggle';
    toggle.setAttribute('aria-label', 'Menú de navegación');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML = '☰';
    navbar.insertBefore(toggle, links);

    toggle.addEventListener('click', () => {
      const isOpen = links.classList.toggle('navbar__links--open');
      toggle.setAttribute('aria-expanded', isOpen.toString());
      toggle.innerHTML = isOpen ? '✕' : '☰';
    });

    links.querySelectorAll('.navbar__link').forEach(link => {
      link.addEventListener('click', () => {
        links.classList.remove('navbar__links--open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.innerHTML = '☰';
      });
    });
  }

  // ===== Setup logout button =====
  function setupLogoutButton() {
    const userDiv = document.querySelector('.navbar__user');
    const logoutBtn = document.createElement('button');
    logoutBtn.id = 'logout-btn';
    logoutBtn.className = 'navbar__logout';
    logoutBtn.textContent = 'Salir';
    logoutBtn.title = 'Cerrar sesión';
    logoutBtn.setAttribute('aria-label', 'Cerrar sesión');
    logoutBtn.style.display = 'none';
    logoutBtn.addEventListener('click', handleLogout);
    userDiv.appendChild(logoutBtn);
  }

  // ===== Keyboard navigation =====
  function setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal-overlay--active');
        if (activeModal) {
          activeModal.classList.remove('modal-overlay--active');
        }
      }
    });
  }

  // ===== Init =====
  function init() {
    setupThemeToggle();
    setupMobileMenu();
    setupLogoutButton();
    setupKeyboardNav();

    // If already authenticated (from refresh), update UI
    if (Auth.isAuthenticated()) {
      onAuthChange(Auth.getUser());
    }

    // Listen for hash changes
    window.addEventListener('hashchange', navigate);

    // Initial navigation
    navigate();
  }

  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return {
    showToast,
    navigate,
    onAuthChange,
    handleLogout,
  };
})();
