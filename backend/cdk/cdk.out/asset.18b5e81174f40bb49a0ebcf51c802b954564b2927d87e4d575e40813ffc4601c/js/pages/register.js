/**
 * Register Page — Multi-tenant registration
 *
 * Two flows:
 * 1. New tenant: Creates a tenant group, registers user as admin
 * 2. Existing tenant: Registers user within an existing tenant (requires tenant code)
 */
const RegisterPage = {
  render() {
    return `
      <div class="login-page">
        <div class="login-card" style="max-width:440px;">
          <div class="login-card__header">
            <img src="assets/images/iso_27001_lead_auditor.svg" alt="Auditor Lead" class="login-card__logo">
            <h1 class="login-card__title">Crear Cuenta</h1>
            <p class="login-card__subtitle">Regístrate para acceder a la plataforma</p>
          </div>

          <!-- Registration type selector -->
          <div class="register-type" role="radiogroup" aria-label="Tipo de registro">
            <button type="button" class="register-type__btn register-type__btn--active" data-type="new-tenant" aria-pressed="true">
              🏢 Nuevo Tenant
            </button>
            <button type="button" class="register-type__btn" data-type="join-tenant" aria-pressed="false">
              👤 Unirme a un Tenant
            </button>
          </div>

          <form id="register-form" class="login-form" novalidate>
            <!-- New Tenant Section -->
            <div id="section-new-tenant">
              <div class="form-group">
                <label for="reg-org-name">Nombre de la organización</label>
                <input type="text" id="reg-org-name" placeholder="Ej: ACME Corp" required>
              </div>
            </div>

            <!-- Join Tenant Section (hidden by default) -->
            <div id="section-join-tenant" style="display:none;">
              <div class="form-group">
                <label for="reg-tenant-code">Código del Tenant</label>
                <input type="text" id="reg-tenant-code" placeholder="Ej: tenant-001">
                <small style="font-size:0.72rem; color:var(--color-text-muted);">Solicita este código al administrador de tu organización</small>
              </div>
            </div>

            <!-- Common fields -->
            <div class="form-group">
              <label for="reg-username">Nombre de usuario</label>
              <input type="text" id="reg-username" required placeholder="Ej: jperez" autocomplete="username">
            </div>

            <div class="form-group">
              <label for="reg-email">Correo electrónico</label>
              <input type="email" id="reg-email" required placeholder="usuario@empresa.com" autocomplete="email">
            </div>

            <div class="form-group">
              <label for="reg-password">Contraseña</label>
              <input type="password" id="reg-password" required placeholder="Mínimo 8 caracteres" autocomplete="new-password" minlength="8">
            </div>

            <div class="form-group">
              <label for="reg-password-confirm">Confirmar contraseña</label>
              <input type="password" id="reg-password-confirm" required placeholder="Repetir contraseña" autocomplete="new-password">
            </div>

            <div id="register-error" class="login-error" role="alert" aria-live="polite" hidden></div>
            <div id="register-success" class="register-success" role="status" aria-live="polite" hidden></div>

            <button type="submit" class="btn btn--primary login-form__submit" id="register-btn">
              Crear cuenta
            </button>
          </form>

          <!-- Confirmation code form (shown after successful registration) -->
          <form id="confirm-form" style="display:none;" class="login-form" novalidate>
            <div class="register-success" style="display:block; margin-bottom:1rem;">
              ✅ Cuenta creada. Revisa tu correo para el código de verificación.
            </div>
            <div class="form-group">
              <label for="confirm-code">Código de verificación</label>
              <input type="text" id="confirm-code" required placeholder="123456" autocomplete="one-time-code" inputmode="numeric" maxlength="6">
            </div>
            <div id="confirm-error" class="login-error" role="alert" hidden></div>
            <button type="submit" class="btn btn--primary login-form__submit" id="confirm-btn">
              Verificar cuenta
            </button>
          </form>

          <p class="login-card__footer">
            ¿Ya tienes cuenta? <a href="#/login" style="color:var(--pico-primary); font-weight:600;">Iniciar sesión</a>
          </p>
        </div>
      </div>
    `;
  },

  afterRender() {
    const form = document.getElementById('register-form');
    const confirmForm = document.getElementById('confirm-form');
    const errorDiv = document.getElementById('register-error');
    const successDiv = document.getElementById('register-success');
    const btn = document.getElementById('register-btn');
    const typeBtns = document.querySelectorAll('.register-type__btn');
    const newTenantSection = document.getElementById('section-new-tenant');
    const joinTenantSection = document.getElementById('section-join-tenant');

    let registrationType = 'new-tenant';
    let registeredUsername = '';

    // Type toggle
    typeBtns.forEach(typeBtn => {
      typeBtn.addEventListener('click', () => {
        typeBtns.forEach(b => { b.classList.remove('register-type__btn--active'); b.setAttribute('aria-pressed', 'false'); });
        typeBtn.classList.add('register-type__btn--active');
        typeBtn.setAttribute('aria-pressed', 'true');
        registrationType = typeBtn.dataset.type;

        newTenantSection.style.display = registrationType === 'new-tenant' ? '' : 'none';
        joinTenantSection.style.display = registrationType === 'join-tenant' ? '' : 'none';

        // Update required attributes
        document.getElementById('reg-org-name').required = registrationType === 'new-tenant';
        document.getElementById('reg-tenant-code').required = registrationType === 'join-tenant';
      });
    });

    // Registration submit
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errorDiv.hidden = true;

      const username = document.getElementById('reg-username').value.trim();
      const email = document.getElementById('reg-email').value.trim();
      const password = document.getElementById('reg-password').value;
      const passwordConfirm = document.getElementById('reg-password-confirm').value;

      // Validate passwords match
      if (password !== passwordConfirm) {
        errorDiv.textContent = 'Las contraseñas no coinciden';
        errorDiv.hidden = false;
        return;
      }

      if (password.length < 8) {
        errorDiv.textContent = 'La contraseña debe tener al menos 8 caracteres';
        errorDiv.hidden = false;
        return;
      }

      // Determine tenant info
      let tenantId, role;
      if (registrationType === 'new-tenant') {
        const orgName = document.getElementById('reg-org-name').value.trim();
        if (!orgName) { errorDiv.textContent = 'Ingresa el nombre de la organización'; errorDiv.hidden = false; return; }
        tenantId = 'tenant-' + orgName.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').slice(0, 32);
        role = 'admin';
      } else {
        tenantId = document.getElementById('reg-tenant-code').value.trim();
        if (!tenantId) { errorDiv.textContent = 'Ingresa el código del tenant'; errorDiv.hidden = false; return; }
        role = 'auditor';
      }

      btn.disabled = true;
      btn.textContent = 'Registrando...';

      try {
        await Auth.signUp(username, password, email, role);
        registeredUsername = username;

        // If new tenant, we'll create the group after confirmation
        sessionStorage.setItem('pending_tenant', JSON.stringify({ tenantId, role, username, registrationType }));

        // Show confirmation form
        form.style.display = 'none';
        confirmForm.style.display = '';
      } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Crear cuenta';
      }
    });

    // Confirmation submit
    confirmForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const code = document.getElementById('confirm-code').value.trim();
      const confirmError = document.getElementById('confirm-error');
      const confirmBtn = document.getElementById('confirm-btn');
      confirmError.hidden = true;

      if (!code || code.length < 6) {
        confirmError.textContent = 'Ingresa el código de 6 dígitos';
        confirmError.hidden = false;
        return;
      }

      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Verificando...';

      try {
        await Auth.confirmSignUp(registeredUsername, code);

        // Get pending tenant info
        const pending = JSON.parse(sessionStorage.getItem('pending_tenant') || '{}');

        App.showToast('¡Cuenta verificada! Puedes iniciar sesión', 'success');
        sessionStorage.removeItem('pending_tenant');

        // Redirect to login
        setTimeout(() => { window.location.hash = '#/login'; }, 1500);
      } catch (error) {
        confirmError.textContent = error.message;
        confirmError.hidden = false;
      } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Verificar cuenta';
      }
    });
  }
};
