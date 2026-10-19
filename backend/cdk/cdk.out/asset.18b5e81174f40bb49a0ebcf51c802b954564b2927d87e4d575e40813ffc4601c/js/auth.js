/**
 * Cognito Auth Module — SaaS multi-tenant authentication
 *
 * Uses Cognito USER_PASSWORD_AUTH flow directly via fetch (no SDK needed).
 * Tokens include tenant context via groups and custom attributes.
 *
 * Best practices followed:
 * - Token stored in memory only (not localStorage) for XSS protection
 * - Refresh token in memory for session continuity
 * - Tenant isolation via Cognito groups (cognito:groups claim in token)
 * - Role-based access via custom:role attribute
 * - Auto-refresh before token expiry
 * - All API calls include Authorization header with ID token
 */
const Auth = (() => {
  // ===== Configuration =====
  const CONFIG = {
    region: 'us-east-1',
    userPoolId: 'us-east-1_mniJzgGj2',
    clientId: '2mqmee5jm62j1q77q6dmmkto34',
  };

  const COGNITO_ENDPOINT = `https://cognito-idp.${CONFIG.region}.amazonaws.com/`;

  // ===== Token State (in-memory only — XSS safe) =====
  let tokens = {
    idToken: null,
    accessToken: null,
    refreshToken: null,
    expiresAt: 0,
  };

  let currentUser = null;
  let refreshTimer = null;

  // ===== Core Auth Methods =====

  /**
   * Sign in with username and password.
   * Returns user info with tenant/role context on success.
   */
  async function signIn(username, password) {
    const payload = {
      AuthFlow: 'USER_PASSWORD_AUTH',
      ClientId: CONFIG.clientId,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password,
      },
    };

    const response = await fetch(COGNITO_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorType = data.__type || 'AuthError';
      const errorMessage = data.message || data.Message || 'Error de autenticación';

      if (errorType.includes('NotAuthorizedException')) {
        throw new Error('Usuario o contraseña incorrectos');
      }
      if (errorType.includes('UserNotFoundException')) {
        throw new Error('Usuario no encontrado');
      }
      if (errorType.includes('NewPasswordRequired')) {
        throw new Error('Se requiere cambiar la contraseña');
      }
      throw new Error(errorMessage);
    }

    // Handle successful auth
    if (data.AuthenticationResult) {
      setTokens(data.AuthenticationResult);
      currentUser = parseIdToken(tokens.idToken);
      scheduleRefresh();
      return currentUser;
    }

    // Handle challenges (NEW_PASSWORD_REQUIRED, etc.)
    if (data.ChallengeName) {
      throw new Error(`Desafío requerido: ${data.ChallengeName}`);
    }

    throw new Error('Respuesta de autenticación inesperada');
  }

  /**
   * Sign out — clear tokens and state.
   */
  function signOut() {
    tokens = { idToken: null, accessToken: null, refreshToken: null, expiresAt: 0 };
    currentUser = null;
    if (refreshTimer) {
      clearTimeout(refreshTimer);
      refreshTimer = null;
    }
  }

  /**
   * Sign up a new user with Cognito.
   */
  async function signUp(username, password, email, role) {
    const payload = {
      ClientId: CONFIG.clientId,
      Username: username,
      Password: password,
      UserAttributes: [
        { Name: 'email', Value: email },
        { Name: 'custom:role', Value: role || 'auditor' },
      ],
    };

    const response = await fetch(COGNITO_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.SignUp',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorType = data.__type || '';
      if (errorType.includes('UsernameExistsException')) throw new Error('El nombre de usuario ya existe');
      if (errorType.includes('InvalidPasswordException')) throw new Error('La contraseña no cumple los requisitos');
      if (errorType.includes('InvalidParameterException')) throw new Error(data.message || 'Parámetros inválidos');
      throw new Error(data.message || 'Error al registrar usuario');
    }

    return { userSub: data.UserSub, confirmed: data.UserConfirmed };
  }

  /**
   * Confirm sign up with verification code.
   */
  async function confirmSignUp(username, code) {
    const payload = {
      ClientId: CONFIG.clientId,
      Username: username,
      ConfirmationCode: code,
    };

    const response = await fetch(COGNITO_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.ConfirmSignUp',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorType = data.__type || '';
      if (errorType.includes('CodeMismatchException')) throw new Error('Código de verificación incorrecto');
      if (errorType.includes('ExpiredCodeException')) throw new Error('El código ha expirado. Solicita uno nuevo');
      throw new Error(data.message || 'Error al verificar cuenta');
    }

    return true;
  }

  /**
   * Refresh the session using the refresh token.
   */
  async function refreshSession() {
    if (!tokens.refreshToken) {
      signOut();
      return false;
    }

    try {
      const payload = {
        AuthFlow: 'REFRESH_TOKEN_AUTH',
        ClientId: CONFIG.clientId,
        AuthParameters: {
          REFRESH_TOKEN: tokens.refreshToken,
        },
      };

      const response = await fetch(COGNITO_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-amz-json-1.1',
          'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        signOut();
        return false;
      }

      const data = await response.json();
      if (data.AuthenticationResult) {
        // Refresh doesn't return a new refresh token
        setTokens({
          ...data.AuthenticationResult,
          RefreshToken: tokens.refreshToken,
        });
        currentUser = parseIdToken(tokens.idToken);
        scheduleRefresh();
        return true;
      }

      signOut();
      return false;
    } catch (e) {
      signOut();
      return false;
    }
  }

  // ===== Token Management =====

  function setTokens(authResult) {
    tokens.idToken = authResult.IdToken;
    tokens.accessToken = authResult.AccessToken;
    if (authResult.RefreshToken) {
      tokens.refreshToken = authResult.RefreshToken;
    }
    // ExpiresIn is in seconds
    tokens.expiresAt = Date.now() + (authResult.ExpiresIn || 3600) * 1000;
  }

  function scheduleRefresh() {
    if (refreshTimer) clearTimeout(refreshTimer);

    // Refresh 5 minutes before expiry
    const refreshIn = tokens.expiresAt - Date.now() - 5 * 60 * 1000;
    if (refreshIn > 0) {
      refreshTimer = setTimeout(() => refreshSession(), refreshIn);
    }
  }

  /**
   * Parse the JWT ID token to extract user claims.
   * ID tokens contain: sub, email, cognito:groups, custom:role, etc.
   */
  function parseIdToken(token) {
    if (!token) return null;

    try {
      const payload = token.split('.')[1];
      const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));

      return {
        username: decoded['cognito:username'] || decoded.sub,
        email: decoded.email || '',
        groups: decoded['cognito:groups'] || [],
        role: decoded['custom:role'] || 'user',
        tenantId: (decoded['cognito:groups'] || [])[0] || 'default',
        sub: decoded.sub,
        tokenExpiry: decoded.exp,
      };
    } catch (e) {
      return null;
    }
  }

  // ===== Public API =====

  return {
    /**
     * Sign in with credentials.
     * @returns {Promise<Object>} User info with tenant context
     */
    signIn,

    /**
     * Sign up a new user.
     * @returns {Promise<Object>} { userSub, confirmed }
     */
    signUp,

    /**
     * Confirm sign up with verification code.
     * @returns {Promise<boolean>}
     */
    confirmSignUp,

    /**
     * Sign out and clear session.
     */
    signOut,

    /**
     * Refresh the current session.
     * @returns {Promise<boolean>} true if refresh succeeded
     */
    refreshSession,

    /**
     * Check if user is currently authenticated.
     * @returns {boolean}
     */
    isAuthenticated() {
      return tokens.idToken !== null && Date.now() < tokens.expiresAt;
    },

    /**
     * Get current user info (from token claims).
     * @returns {Object|null} User with username, email, role, tenantId, groups
     */
    getUser() {
      return currentUser;
    },

    /**
     * Get the ID token for API authorization headers.
     * @returns {string|null}
     */
    getIdToken() {
      if (!this.isAuthenticated()) return null;
      return tokens.idToken;
    },

    /**
     * Get the access token.
     * @returns {string|null}
     */
    getAccessToken() {
      if (!this.isAuthenticated()) return null;
      return tokens.accessToken;
    },

    /**
     * Get authorization headers for API calls.
     * Includes token and tenant context following SaaS best practices.
     * @returns {Object} Headers object
     */
    getAuthHeaders() {
      const headers = {};
      if (tokens.idToken) {
        headers['Authorization'] = `Bearer ${tokens.idToken}`;
      }
      if (currentUser) {
        headers['X-Tenant-Id'] = currentUser.tenantId;
        headers['X-User-Role'] = currentUser.role;
      }
      return headers;
    },

    /**
     * Get Cognito configuration (for display/debug).
     */
    getConfig() {
      return { ...CONFIG };
    },
  };
})();
