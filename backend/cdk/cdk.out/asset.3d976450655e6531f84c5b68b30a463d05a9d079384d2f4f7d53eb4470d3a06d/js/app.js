/**
 * Auditor Lead - SPA Router y App principal
 */
const App = (() => {
  const appContainer = document.getElementById('app');
  let currentRoute = '';

  // ===== Rutas =====
  const routes = {
    '/': { page: LandingPage, nav: 'home' },
    '/acerca': { page: AcercaPage, nav: 'acerca' },
    '/auditorias': { page: AuditoriasPage, nav: 'auditorias' },
    '/evaluaciones': { page: EvaluacionesPage, nav: 'evaluaciones' }
  };

  // ===== Router =====
  function getRoute() {
    const hash = window.location.hash.slice(1) || '/';
    return hash;
  }

  function parseRoute(path) {
    // Check for audit detail route: /auditorias/:id
    const auditoriaMatch = path.match(/^\/auditorias\/(\d+)$/);
    if (auditoriaMatch) {
      return { page: AuditoriaDetallePage, nav: 'auditorias', params: { id: auditoriaMatch[1] } };
    }

    // Standard routes
    return routes[path] || routes['/'];
  }

  async function navigate() {
    const path = getRoute();

    if (path === currentRoute) return;
    currentRoute = path;

    const { page, nav, params } = parseRoute(path);

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

  // ===== Toast notifications =====
  let toastTimeout = null;

  function showToast(message, type = 'info') {
    // Remove existing toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);

    // Show
    requestAnimationFrame(() => {
      toast.classList.add('toast--visible');
    });

    // Hide after 3s
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toast.classList.remove('toast--visible');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // ===== Mobile Menu =====
  function setupMobileMenu() {
    const navbar = document.querySelector('.navbar__container');
    const links = document.querySelector('.navbar__links');

    // Add toggle button
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

    // Close menu on link click
    links.querySelectorAll('.navbar__link').forEach(link => {
      link.addEventListener('click', () => {
        links.classList.remove('navbar__links--open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.innerHTML = '☰';
      });
    });
  }

  // ===== Keyboard navigation =====
  function setupKeyboardNav() {
    document.addEventListener('keydown', (e) => {
      // Close modals on Escape
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
    setupMobileMenu();
    setupKeyboardNav();

    // Listen for hash changes
    window.addEventListener('hashchange', navigate);

    // Initial navigation
    navigate();
  }

  // Start the app
  document.addEventListener('DOMContentLoaded', init);

  // Public API
  return {
    showToast,
    navigate
  };
})();
