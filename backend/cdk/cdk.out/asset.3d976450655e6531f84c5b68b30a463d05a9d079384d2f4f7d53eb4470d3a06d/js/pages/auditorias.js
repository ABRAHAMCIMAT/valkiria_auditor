/**
 * Auditorias Page - Lista de auditorías
 */
const AuditoriasPage = {
  render() {
    return `
      <div class="page-header">
        <div class="page-header__container">
          <h1 class="page-header__title">Auditorias</h1>
          <p class="page-header__subtitle">Gestiona tus proyectos de auditoría ISO 27001</p>
        </div>
      </div>

      <div class="page-content">
        <div class="toolbar">
          <div class="toolbar__left">
            <button class="btn btn--auditorias" id="btn-nueva-auditoria" aria-haspopup="dialog">
              Nueva Auditoria
            </button>
            <div class="select-wrapper">
              <label for="filter-iso-version" class="sr-only">Filtrar por versión ISO</label>
              <select id="filter-iso-version" aria-label="Filtrar por versión ISO">
                <option value="todas">Todas las versiones</option>
                <option value="2022">ISO 27001:2022</option>
                <option value="2013">ISO 27001:2013</option>
              </select>
            </div>
          </div>
        </div>

        <div class="table-container" role="region" aria-label="Tabla de auditorías">
          <table class="table" id="tabla-auditorias">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Auditoria</th>
                <th scope="col">Versión ISO</th>
                <th scope="col">Creada</th>
                <th scope="col">Actualización</th>
                <th scope="col">Completada</th>
                <th scope="col">Acciones</th>
              </tr>
            </thead>
            <tbody id="auditorias-tbody">
              <tr>
                <td colspan="7">
                  <div class="loading"><div class="loading__spinner"></div></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Modal Nueva Auditoria -->
      <div class="modal-overlay" id="modal-auditoria" role="dialog" aria-modal="true" aria-labelledby="modal-auditoria-title">
        <div class="modal">
          <div class="modal__header">
            <h2 id="modal-auditoria-title" class="modal__title">Nueva Auditoria</h2>
            <button class="modal__close" id="modal-auditoria-close" aria-label="Cerrar">&times;</button>
          </div>
          <form id="form-auditoria">
            <div class="form-group">
              <label for="auditoria-nombre">Nombre de la auditoría</label>
              <input type="text" id="auditoria-nombre" required placeholder="Ej: Auditoria Empresa X">
            </div>
            <div class="form-group">
              <label for="auditoria-iso-version">Versión ISO</label>
              <select id="auditoria-iso-version" required>
                <option value="">Seleccionar versión...</option>
                <option value="2022">ISO/IEC 27001:2022 (93 controles, 4 dominios)</option>
                <option value="2013">ISO/IEC 27001:2013 (114 controles, 14 dominios)</option>
              </select>
            </div>
            <div class="form-group" id="framework-group" style="display:none;">
              <label for="auditoria-framework">Framework de ejecución</label>
              <select id="auditoria-framework">
                <option value="strands">Strands Agents</option>
                <option value="langgraph">LangGraph</option>
                <option value="crewai">CrewAI</option>
              </select>
            </div>
            <div class="form-group">
              <label for="auditoria-descripcion">Descripción (opcional)</label>
              <textarea id="auditoria-descripcion" placeholder="Describe el alcance de la auditoría..."></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn--primary" id="btn-cancelar-auditoria" style="background:#999;">Cancelar</button>
              <button type="submit" class="btn btn--auditorias">Crear Auditoria</button>
            </div>
          </form>
        </div>
      </div>
    `;
  },

  async afterRender() {
    const tbody = document.getElementById('auditorias-tbody');
    const modal = document.getElementById('modal-auditoria');
    const btnNueva = document.getElementById('btn-nueva-auditoria');
    const btnClose = document.getElementById('modal-auditoria-close');
    const btnCancelar = document.getElementById('btn-cancelar-auditoria');
    const form = document.getElementById('form-auditoria');
    const isoSelect = document.getElementById('auditoria-iso-version');
    const frameworkGroup = document.getElementById('framework-group');
    const filterIso = document.getElementById('filter-iso-version');

    // Cargar datos
    await this.loadData(tbody);

    // Filtro por versión ISO
    filterIso.addEventListener('change', () => this.loadData(tbody, filterIso.value));

    // Modal handlers
    btnNueva.addEventListener('click', () => this.openModal(modal));
    btnClose.addEventListener('click', () => this.closeModal(modal));
    btnCancelar.addEventListener('click', () => this.closeModal(modal));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.closeModal(modal);
    });

    // Mostrar/ocultar framework según versión ISO
    isoSelect.addEventListener('change', () => {
      frameworkGroup.style.display = isoSelect.value === '2022' ? 'block' : 'none';
    });

    // Crear auditoría
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nombre = document.getElementById('auditoria-nombre').value;
      const isoVersion = isoSelect.value;
      const framework = document.getElementById('auditoria-framework').value;
      const descripcion = document.getElementById('auditoria-descripcion').value;

      try {
        await API.createAuditoria({ nombre, isoVersion, framework, descripcion });
        await API.ejecutarAuditoria(isoVersion, framework);
        this.closeModal(modal);
        form.reset();
        frameworkGroup.style.display = 'none';
        await this.loadData(tbody, filterIso.value);
        App.showToast('Auditoría creada exitosamente', 'success');
      } catch (error) {
        App.showToast('Error al crear auditoría', 'error');
      }
    });
  },

  async loadData(tbody, filter = 'todas') {
    try {
      let auditorias = await API.getAuditorias();

      if (filter !== 'todas') {
        auditorias = auditorias.filter(a => a.isoVersion === filter);
      }

      if (auditorias.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7">
              <div class="empty-state">
                <div class="empty-state__icon">📋</div>
                <p class="empty-state__text">No hay auditorías registradas</p>
              </div>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = auditorias.map((a, i) => `
        <tr>
          <td>${i + 1}</td>
          <td><a href="#/auditorias/${a.id}" class="table__link">${a.nombre}</a></td>
          <td><span class="badge badge--info">ISO ${a.isoVersion}</span></td>
          <td>${a.creada}</td>
          <td>${a.actualizacion}</td>
          <td>${a.completada || '<span class="badge badge--pending">Pendiente</span>'}</td>
          <td>
            <div class="table__actions">
              <button class="table__action-btn table__action-btn--view" 
                      onclick="location.hash='#/auditorias/${a.id}'" 
                      title="Ver detalle" aria-label="Ver detalle de ${a.nombre}">👁️</button>
              <button class="table__action-btn table__action-btn--delete" 
                      data-id="${a.id}" 
                      title="Eliminar" aria-label="Eliminar ${a.nombre}">🗑️</button>
            </div>
          </td>
        </tr>
      `).join('');

      // Delete handlers
      tbody.querySelectorAll('.table__action-btn--delete').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (confirm('¿Estás seguro de eliminar esta auditoría?')) {
            await API.deleteAuditoria(btn.dataset.id);
            await this.loadData(tbody, document.getElementById('filter-iso-version').value);
            App.showToast('Auditoría eliminada', 'success');
          }
        });
      });
    } catch (error) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7">
            <div class="empty-state">
              <div class="empty-state__icon">⚠️</div>
              <p class="empty-state__text">Error al cargar auditorías</p>
            </div>
          </td>
        </tr>
      `;
    }
  },

  openModal(modal) {
    modal.classList.add('modal-overlay--active');
    modal.querySelector('input, select').focus();
  },

  closeModal(modal) {
    modal.classList.remove('modal-overlay--active');
  }
};
