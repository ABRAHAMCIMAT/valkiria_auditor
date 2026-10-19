/**
 * Auditorias Page - Lista de auditorías con carga de datos de evaluación
 */
const AuditoriasPage = {
  uploadedFiles: [],

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
              + Nueva Auditoria
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
                <th scope="col">Datos cargados</th>
                <th scope="col">Creada</th>
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
        <div class="modal" style="max-width:600px;">
          <div class="modal__header">
            <h2 id="modal-auditoria-title" class="modal__title">Nueva Auditoria</h2>
            <button class="modal__close" id="modal-auditoria-close" aria-label="Cerrar">&times;</button>
          </div>
          <form id="form-auditoria">
            <div class="form-group">
              <label for="auditoria-nombre">Nombre de la auditoría</label>
              <input type="text" id="auditoria-nombre" required placeholder="Ej: Auditoria Empresa X - App Backend">
            </div>

            <div class="form-row">
              <div class="form-group" style="flex:1;">
                <label for="auditoria-iso-version">Versión ISO</label>
                <select id="auditoria-iso-version" required>
                  <option value="">Seleccionar versión...</option>
                  <option value="2022">ISO/IEC 27001:2022 (93 controles)</option>
                  <option value="2013">ISO/IEC 27001:2013 (114 controles)</option>
                </select>
              </div>
              <div class="form-group" id="framework-group" style="flex:1; display:none;">
                <label for="auditoria-framework">Framework</label>
                <select id="auditoria-framework">
                  <option value="strands">Strands Agents</option>
                  <option value="langgraph">LangGraph</option>
                  <option value="crewai">CrewAI</option>
                </select>
              </div>
            </div>

            <!-- Evaluation Data Upload Section -->
            <fieldset class="upload-fieldset">
              <legend>Datos de evaluación</legend>
              <p class="upload-fieldset__hint">
                Carga resultados de análisis de seguridad para la evaluación automatizada. 
                Formatos aceptados: Markdown (.md), JSON, XML, HTML, CSV, o un archivo .zip con todos los recursos.
              </p>

              <div class="upload-tabs" role="tablist">
                <button type="button" class="upload-tab upload-tab--active" role="tab" data-tab="files" aria-selected="true">
                  📄 Archivos individuales
                </button>
                <button type="button" class="upload-tab" role="tab" data-tab="zip">
                  📦 Archivo .zip
                </button>
              </div>

              <!-- Tab: Individual files -->
              <div class="upload-tab-content" id="tab-files">
                <div class="upload-area" id="upload-area-files" role="button" tabindex="0" aria-label="Arrastrar archivos de evaluación">
                  <div class="upload-area__icon">📁</div>
                  <p class="upload-area__text"><strong>Arrastra archivos aquí</strong> o haz clic para seleccionar</p>
                  <p class="upload-area__text" style="font-size:0.75rem; margin-top:0.3rem; opacity:0.7;">
                    SonarQube (.json, .md) · OWASP ZAP (.xml, .json, .html) · Dependency Check (.csv, .json) · Reportes Markdown
                  </p>
                </div>
                <input type="file" id="auditoria-archivos" multiple accept=".md,.json,.xml,.html,.csv,.txt,.yaml,.yml" style="display:none;" aria-label="Seleccionar archivos">
              </div>

              <!-- Tab: ZIP upload -->
              <div class="upload-tab-content" id="tab-zip" style="display:none;">
                <div class="upload-area" id="upload-area-zip" role="button" tabindex="0" aria-label="Arrastrar archivo ZIP">
                  <div class="upload-area__icon">📦</div>
                  <p class="upload-area__text"><strong>Arrastra un archivo .zip</strong> o haz clic para seleccionar</p>
                  <p class="upload-area__text" style="font-size:0.75rem; margin-top:0.3rem; opacity:0.7;">
                    Incluye código fuente, configuraciones, y resultados de análisis en un solo archivo (máx. 50MB)
                  </p>
                </div>
                <input type="file" id="auditoria-zip" accept=".zip" style="display:none;" aria-label="Seleccionar archivo ZIP">
              </div>

              <!-- File list -->
              <div id="uploaded-files-list" class="uploaded-files" aria-live="polite"></div>
            </fieldset>

            <div class="form-group">
              <label for="auditoria-descripcion">Contexto organizacional (opcional)</label>
              <textarea id="auditoria-descripcion" placeholder="Describe la organización, tamaño, sector, y alcance de la auditoría..."></textarea>
            </div>

            <div class="form-actions">
              <button type="button" class="btn btn--sm" id="btn-cancelar-auditoria" style="background:var(--color-text-muted); color:#fff;">Cancelar</button>
              <button type="submit" class="btn btn--auditorias" id="btn-crear-auditoria">Crear y ejecutar auditoría</button>
            </div>
          </form>
        </div>
      </div>
    `;
  },

  async afterRender() {
    this.uploadedFiles = [];

    const tbody = document.getElementById('auditorias-tbody');
    const modal = document.getElementById('modal-auditoria');
    const btnNueva = document.getElementById('btn-nueva-auditoria');
    const btnClose = document.getElementById('modal-auditoria-close');
    const btnCancelar = document.getElementById('btn-cancelar-auditoria');
    const form = document.getElementById('form-auditoria');
    const isoSelect = document.getElementById('auditoria-iso-version');
    const frameworkGroup = document.getElementById('framework-group');
    const filterIso = document.getElementById('filter-iso-version');

    // Upload elements
    const uploadAreaFiles = document.getElementById('upload-area-files');
    const uploadAreaZip = document.getElementById('upload-area-zip');
    const fileInput = document.getElementById('auditoria-archivos');
    const zipInput = document.getElementById('auditoria-zip');
    const filesList = document.getElementById('uploaded-files-list');
    const tabs = document.querySelectorAll('.upload-tab');

    // Load data
    await this.loadData(tbody);

    // Filter
    filterIso.addEventListener('change', () => this.loadData(tbody, filterIso.value));

    // Modal handlers
    btnNueva.addEventListener('click', () => this.openModal(modal));
    btnClose.addEventListener('click', () => this.closeModal(modal));
    btnCancelar.addEventListener('click', () => this.closeModal(modal));
    modal.addEventListener('click', (e) => { if (e.target === modal) this.closeModal(modal); });

    // ISO version toggle
    isoSelect.addEventListener('change', () => {
      frameworkGroup.style.display = isoSelect.value === '2022' ? 'block' : 'none';
    });

    // Tab switching
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => { t.classList.remove('upload-tab--active'); t.setAttribute('aria-selected', 'false'); });
        tab.classList.add('upload-tab--active');
        tab.setAttribute('aria-selected', 'true');
        document.getElementById('tab-files').style.display = tab.dataset.tab === 'files' ? '' : 'none';
        document.getElementById('tab-zip').style.display = tab.dataset.tab === 'zip' ? '' : 'none';
      });
    });

    // File upload — individual files
    this.setupUploadArea(uploadAreaFiles, fileInput, filesList, false);
    // File upload — zip
    this.setupUploadArea(uploadAreaZip, zipInput, filesList, true);

    // Submit
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nombre = document.getElementById('auditoria-nombre').value;
      const isoVersion = isoSelect.value;
      const framework = document.getElementById('auditoria-framework').value;
      const descripcion = document.getElementById('auditoria-descripcion').value;

      const btn = document.getElementById('btn-crear-auditoria');
      btn.disabled = true;
      btn.textContent = 'Creando...';

      try {
        const auditData = {
          nombre,
          isoVersion,
          framework: isoVersion === '2022' ? framework : 'comp2013',
          descripcion,
          archivos: this.uploadedFiles.map(f => ({ name: f.name, size: f.size, type: f.type })),
        };

        await API.createAuditoria(auditData);
        await API.ejecutarAuditoria(isoVersion, framework);

        this.closeModal(modal);
        form.reset();
        this.uploadedFiles = [];
        filesList.innerHTML = '';
        frameworkGroup.style.display = 'none';
        await this.loadData(tbody, filterIso.value);
        App.showToast('Auditoría creada y en ejecución', 'success');
      } catch (error) {
        App.showToast('Error al crear auditoría', 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Crear y ejecutar auditoría';
      }
    });
  },

  setupUploadArea(area, input, listEl, isZip) {
    area.addEventListener('click', () => input.click());
    area.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });

    area.addEventListener('dragover', (e) => { e.preventDefault(); area.classList.add('upload-area--active'); });
    area.addEventListener('dragleave', () => area.classList.remove('upload-area--active'));
    area.addEventListener('drop', (e) => {
      e.preventDefault();
      area.classList.remove('upload-area--active');
      this.handleFiles(e.dataTransfer.files, listEl, isZip);
    });

    input.addEventListener('change', () => this.handleFiles(input.files, listEl, isZip));
  },

  handleFiles(files, listEl, isZip) {
    const newFiles = Array.from(files);

    if (isZip) {
      // Only accept one zip, replace any existing
      const zip = newFiles.find(f => f.name.endsWith('.zip'));
      if (!zip) { App.showToast('Solo se aceptan archivos .zip', 'error'); return; }
      if (zip.size > 50 * 1024 * 1024) { App.showToast('El archivo excede 50MB', 'error'); return; }
      this.uploadedFiles = [zip];
    } else {
      // Add multiple files (filter by accepted types)
      const accepted = ['.md', '.json', '.xml', '.html', '.csv', '.txt', '.yaml', '.yml'];
      const valid = newFiles.filter(f => accepted.some(ext => f.name.toLowerCase().endsWith(ext)));
      if (valid.length < newFiles.length) {
        App.showToast(`${newFiles.length - valid.length} archivo(s) con formato no soportado`, 'error');
      }
      this.uploadedFiles = [...this.uploadedFiles, ...valid];
    }

    this.renderFileList(listEl);
  },

  renderFileList(listEl) {
    if (this.uploadedFiles.length === 0) {
      listEl.innerHTML = '';
      return;
    }

    const iconMap = {
      '.json': '📊', '.xml': '📋', '.html': '🌐', '.md': '📝',
      '.csv': '📈', '.txt': '📄', '.yaml': '⚙️', '.yml': '⚙️', '.zip': '📦',
    };

    listEl.innerHTML = `
      <div class="uploaded-files__header">
        <span>${this.uploadedFiles.length} archivo${this.uploadedFiles.length > 1 ? 's' : ''} seleccionado${this.uploadedFiles.length > 1 ? 's' : ''}</span>
        <button type="button" class="uploaded-files__clear" aria-label="Eliminar todos">✕ Limpiar</button>
      </div>
      <div class="uploaded-files__list">
        ${this.uploadedFiles.map((f, i) => {
          const ext = '.' + f.name.split('.').pop().toLowerCase();
          const icon = iconMap[ext] || '📄';
          const size = f.size < 1024 ? `${f.size}B` : f.size < 1048576 ? `${(f.size/1024).toFixed(1)}KB` : `${(f.size/1048576).toFixed(1)}MB`;
          const label = this.getFileLabel(f.name);
          return `
            <div class="uploaded-file">
              <span class="uploaded-file__icon">${icon}</span>
              <div class="uploaded-file__info">
                <span class="uploaded-file__name">${f.name}</span>
                <span class="uploaded-file__meta">${size}${label ? ' · ' + label : ''}</span>
              </div>
              <button type="button" class="uploaded-file__remove" data-index="${i}" aria-label="Eliminar ${f.name}">✕</button>
            </div>
          `;
        }).join('')}
      </div>
    `;

    // Clear all button
    listEl.querySelector('.uploaded-files__clear').addEventListener('click', () => {
      this.uploadedFiles = [];
      this.renderFileList(listEl);
    });

    // Individual remove buttons
    listEl.querySelectorAll('.uploaded-file__remove').forEach(btn => {
      btn.addEventListener('click', () => {
        this.uploadedFiles.splice(parseInt(btn.dataset.index), 1);
        this.renderFileList(listEl);
      });
    });
  },

  getFileLabel(filename) {
    const lower = filename.toLowerCase();
    if (lower.includes('sonar')) return 'SonarQube';
    if (lower.includes('owasp') || lower.includes('zap')) return 'OWASP ZAP';
    if (lower.includes('dependency') || lower.includes('dep-check')) return 'Dependency Check';
    if (lower.includes('sast')) return 'SAST';
    if (lower.includes('dast')) return 'DAST';
    if (lower.includes('pentest')) return 'Pentest';
    if (lower.includes('trivy')) return 'Trivy';
    if (lower.includes('snyk')) return 'Snyk';
    if (lower.includes('checkov')) return 'Checkov';
    return '';
  },

  async loadData(tbody, filter = 'todas') {
    try {
      let auditorias = await API.getAuditorias();
      if (filter !== 'todas') auditorias = auditorias.filter(a => a.isoVersion === filter);

      if (auditorias.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-state__icon">📋</div><p class="empty-state__text">No hay auditorías registradas</p></div></td></tr>`;
        return;
      }

      tbody.innerHTML = auditorias.map((a, i) => `
        <tr>
          <td>${i + 1}</td>
          <td><a href="#/auditorias/${a.id}" class="table__link">${a.nombre}</a></td>
          <td><span class="badge badge--info">ISO ${a.isoVersion}</span></td>
          <td>${a.archivos ? `<span class="badge badge--complete">${a.archivos.length} archivo${a.archivos.length > 1 ? 's' : ''}</span>` : '<span style="opacity:0.5;">—</span>'}</td>
          <td>${a.creada}</td>
          <td>${a.completada || '<span class="badge badge--pending">Pendiente</span>'}</td>
          <td>
            <div class="table__actions">
              <button class="table__action-btn" onclick="location.hash='#/auditorias/${a.id}'" title="Ver detalle" aria-label="Ver detalle">👁️</button>
              <button class="table__action-btn table__action-btn--delete" data-id="${a.id}" title="Eliminar" aria-label="Eliminar">🗑️</button>
            </div>
          </td>
        </tr>
      `).join('');

      tbody.querySelectorAll('.table__action-btn--delete').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (confirm('¿Eliminar esta auditoría?')) {
            await API.deleteAuditoria(btn.dataset.id);
            await this.loadData(tbody, document.getElementById('filter-iso-version').value);
            App.showToast('Auditoría eliminada', 'success');
          }
        });
      });
    } catch (error) {
      tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-state__icon">⚠️</div><p class="empty-state__text">Error al cargar auditorías</p></div></td></tr>`;
    }
  },

  openModal(modal) { modal.classList.add('modal-overlay--active'); modal.querySelector('input, select').focus(); },
  closeModal(modal) { modal.classList.remove('modal-overlay--active'); }
};
