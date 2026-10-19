/**
 * Evaluaciones Page - Lista de evaluaciones
 */
const EvaluacionesPage = {
  render() {
    return `
      <div class="page-header">
        <div class="page-header__container">
          <h1 class="page-header__title">Evaluaciones</h1>
          <p class="page-header__subtitle">Gestiona las evaluaciones de cumplimiento ISO 27001</p>
        </div>
      </div>

      <div class="page-content">
        <div class="toolbar">
          <div class="toolbar__left">
            <button class="btn btn--evaluaciones" id="btn-nueva-evaluacion" aria-haspopup="dialog">
              Nueva Evaluación
            </button>
            <div class="select-wrapper">
              <label for="filter-eval-iso" class="sr-only">Filtrar por versión ISO</label>
              <select id="filter-eval-iso" aria-label="Filtrar por versión ISO">
                <option value="todas">Todas las versiones</option>
                <option value="2022">ISO 27001:2022</option>
                <option value="2013">ISO 27001:2013</option>
              </select>
            </div>
          </div>
        </div>

        <div class="table-container" role="region" aria-label="Tabla de evaluaciones">
          <table class="table" id="tabla-evaluaciones">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Evaluación</th>
                <th scope="col">Versión ISO</th>
                <th scope="col">Creada</th>
                <th scope="col">Actualización</th>
                <th scope="col">Estado</th>
                <th scope="col">Resultado</th>
              </tr>
            </thead>
            <tbody id="evaluaciones-tbody">
              <tr>
                <td colspan="7">
                  <div class="loading"><div class="loading__spinner"></div></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Modal Nueva Evaluación -->
      <div class="modal-overlay" id="modal-evaluacion" role="dialog" aria-modal="true" aria-labelledby="modal-evaluacion-title">
        <div class="modal">
          <div class="modal__header">
            <h2 id="modal-evaluacion-title" class="modal__title">Nueva Evaluación</h2>
            <button class="modal__close" id="modal-evaluacion-close" aria-label="Cerrar">&times;</button>
          </div>
          <form id="form-evaluacion">
            <div class="form-group">
              <label for="evaluacion-nombre">Nombre de la evaluación</label>
              <input type="text" id="evaluacion-nombre" required placeholder="Ej: Evaluación App Financiera">
            </div>
            <div class="form-group">
              <label for="evaluacion-iso-version">Versión ISO</label>
              <select id="evaluacion-iso-version" required>
                <option value="">Seleccionar versión...</option>
                <option value="2022">ISO/IEC 27001:2022 (93 controles, 4 dominios)</option>
                <option value="2013">ISO/IEC 27001:2013 (114 controles, 14 dominios)</option>
              </select>
            </div>
            <div class="form-group">
              <label for="evaluacion-recursos">Recursos</label>
              <div class="upload-area" id="upload-area" role="button" tabindex="0" aria-label="Área de carga de archivos">
                <div class="upload-area__icon">📁</div>
                <p class="upload-area__text">Arrastra archivos aquí o haz clic para seleccionar</p>
                <p class="upload-area__text" style="font-size:0.8rem; margin-top:0.5rem;">Código fuente, configuraciones, documentación</p>
              </div>
              <input type="file" id="evaluacion-archivos" multiple style="display:none;" aria-label="Seleccionar archivos">
              <div id="archivos-lista" style="margin-top:0.5rem; font-size:0.85rem;"></div>
            </div>
            <div class="form-group">
              <label for="evaluacion-endpoints">Endpoints (uno por línea)</label>
              <textarea id="evaluacion-endpoints" placeholder="https://api.ejemplo.com/v1&#10;https://api.ejemplo.com/v2"></textarea>
            </div>
            <div class="form-group">
              <label for="evaluacion-conexiones">Conexiones / Fuentes tecnológicas</label>
              <textarea id="evaluacion-conexiones" placeholder="Describe las conexiones con sistemas externos..."></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn--primary" id="btn-cancelar-evaluacion" style="background:#999;">Cancelar</button>
              <button type="submit" class="btn btn--evaluaciones">Crear Evaluación</button>
            </div>
          </form>
        </div>
      </div>
    `;
  },

  async afterRender() {
    const tbody = document.getElementById('evaluaciones-tbody');
    const modal = document.getElementById('modal-evaluacion');
    const btnNueva = document.getElementById('btn-nueva-evaluacion');
    const btnClose = document.getElementById('modal-evaluacion-close');
    const btnCancelar = document.getElementById('btn-cancelar-evaluacion');
    const form = document.getElementById('form-evaluacion');
    const filterIso = document.getElementById('filter-eval-iso');
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('evaluacion-archivos');
    const archivosLista = document.getElementById('archivos-lista');

    // Cargar datos
    await this.loadData(tbody);

    // Filtro
    filterIso.addEventListener('change', () => this.loadData(tbody, filterIso.value));

    // Modal handlers
    btnNueva.addEventListener('click', () => this.openModal(modal));
    btnClose.addEventListener('click', () => this.closeModal(modal));
    btnCancelar.addEventListener('click', () => this.closeModal(modal));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.closeModal(modal);
    });

    // Upload area
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInput.click();
      }
    });

    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('upload-area--active');
    });

    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('upload-area--active');
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('upload-area--active');
      this.handleFiles(e.dataTransfer.files, archivosLista);
    });

    fileInput.addEventListener('change', () => {
      this.handleFiles(fileInput.files, archivosLista);
    });

    // Crear evaluación
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nombre = document.getElementById('evaluacion-nombre').value;
      const isoVersion = document.getElementById('evaluacion-iso-version').value;
      const endpoints = document.getElementById('evaluacion-endpoints').value;
      const conexiones = document.getElementById('evaluacion-conexiones').value;

      try {
        await API.createEvaluacion({ nombre, isoVersion, endpoints, conexiones });
        this.closeModal(modal);
        form.reset();
        archivosLista.innerHTML = '';
        await this.loadData(tbody, filterIso.value);
        App.showToast('Evaluación creada exitosamente', 'success');
      } catch (error) {
        App.showToast('Error al crear evaluación', 'error');
      }
    });
  },

  handleFiles(files, container) {
    const fileNames = Array.from(files).map(f => f.name);
    container.innerHTML = fileNames.map(name => `
      <span style="display:inline-block; background:#f0f0f0; padding:0.2rem 0.5rem; border-radius:4px; margin:0.2rem; font-size:0.8rem;">
        📄 ${name}
      </span>
    `).join('');
  },

  async loadData(tbody, filter = 'todas') {
    try {
      let evaluaciones = await API.getEvaluaciones();

      if (filter !== 'todas') {
        evaluaciones = evaluaciones.filter(e => e.isoVersion === filter);
      }

      if (evaluaciones.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7">
              <div class="empty-state">
                <div class="empty-state__icon">📊</div>
                <p class="empty-state__text">No hay evaluaciones registradas</p>
              </div>
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = evaluaciones.map((e, i) => `
        <tr>
          <td>${i + 1}</td>
          <td>${e.nombre}</td>
          <td><span class="badge badge--info">ISO ${e.isoVersion}</span></td>
          <td>${e.creada}</td>
          <td>${e.actualizacion}</td>
          <td><span class="badge badge--${e.estado === 'completada' ? 'complete' : 'pending'}">${e.estado}</span></td>
          <td>${e.resultado !== null ? `<strong>${e.resultado}%</strong>` : '—'}</td>
        </tr>
      `).join('');
    } catch (error) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7">
            <div class="empty-state">
              <div class="empty-state__icon">⚠️</div>
              <p class="empty-state__text">Error al cargar evaluaciones</p>
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
