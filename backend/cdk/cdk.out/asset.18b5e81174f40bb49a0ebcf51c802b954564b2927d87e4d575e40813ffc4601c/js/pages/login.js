/**
 * Login Page — Cognito authentication
 */
const LoginPage = {
  render() {
    return `
      <div class="login-page">
        <div class="login-card">
          <div class="login-card__header">
            <img src="assets/images/iso_27001_lead_auditor.svg" alt="Auditor Lead" class="login-card__logo">
            <h1 class="login-card__title">Auditor Lead</h1>
            <p class="login-card__subtitle">Plataforma de Auditoría ISO 27001</p>
          </div>
          <form id="login-form" class="login-form" novalidate>
            <div class="form-group">
              <label for="login-username">Usuario</label>
              <input type="text" id="login-username" required placeholder="Nombre de usuario" autocomplete="username" autofocus>
            </div>
            <div class="form-group">
              <label for="login-password">Contraseña</label>
              <input type="password" id="login-password" required placeholder="Contraseña" autocomplete="current-password">
            </div>
            <div id="login-error" class="login-error" role="alert" aria-live="polite" hidden></div>
            <button type="submit" class="btn btn--primary login-form__submit" id="login-btn">
              Iniciar Sesión
            </button>
          </form>
          <p class="login-card__footer">
            Acceso exclusivo para auditores autorizados<br>
            <a href="#/register" style="color:var(--pico-primary); font-weight:600; font-size:0.85rem;">Crear una cuenta</a>
          </p>
        </div>
      </div>
    `;
  },

  afterRender() {
    const form = document.getElementById('login-form');
    const errorDiv = document.getElementById('login-error');
    const btn = document.getElementById('login-btn');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorDiv.hidden = true;

      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value;

      if (!username || !password) {
        errorDiv.textContent = 'Ingresa usuario y contraseña';
        errorDiv.hidden = false;
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Autenticando...';

      try {
        const user = await Auth.signIn(username, password);
        // Update navbar with user info
        App.onAuthChange(user);
        // Navigate to home
        window.location.hash = '#/';
      } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Iniciar Sesión';
      }
    });
  }
};
