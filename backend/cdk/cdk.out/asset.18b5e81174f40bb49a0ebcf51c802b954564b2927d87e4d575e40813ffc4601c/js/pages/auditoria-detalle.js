/**
 * Auditoria Detalle Page - Detalle de una auditoría
 */
const AuditoriaDetallePage = {
  render(id) {
    return `
      <div class="page-header">
        <div class="page-header__container">
          <h1 class="page-header__title">Detalle de Auditoría</h1>
        </div>
      </div>

      <div class="page-content">
        <a href="#/auditorias" class="back-link">← Volver a Auditorías</a>
        
        <div id="detalle-content">
          <div class="loading"><div class="loading__spinner"></div></div>
        </div>
      </div>
    `;
  },

  async afterRender(id) {
    const container = document.getElementById('detalle-content');

    try {
      const auditoria = await API.getAuditoria(id);
      container.innerHTML = this.renderDetail(auditoria);
    } catch (error) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">⚠️</div>
          <p class="empty-state__text">Error al cargar el detalle de la auditoría</p>
        </div>
      `;
    }
  },

  renderDetail(a) {
    const severityCount = {
      alta: a.hallazgos.filter(h => h.severidad === 'alta').length,
      media: a.hallazgos.filter(h => h.severidad === 'media').length,
      baja: a.hallazgos.filter(h => h.severidad === 'baja').length
    };

    const porcentajeConformidad = Math.round((a.resumen.conformes / a.resumen.total_controles) * 100);

    return `
      <!-- Info General -->
      <div class="detail-grid">
        <div class="detail-card">
          <h2 class="detail-card__title">Información General</h2>
          <dl style="display:grid; grid-template-columns: auto 1fr; gap: 0.5rem 1rem; font-size: 0.9rem;">
            <dt style="font-weight:600;">Nombre:</dt>
            <dd>${a.nombre}</dd>
            <dt style="font-weight:600;">Versión ISO:</dt>
            <dd><span class="badge badge--info">ISO 27001:${a.isoVersion}</span></dd>
            <dt style="font-weight:600;">Framework:</dt>
            <dd>${a.framework}</dd>
            <dt style="font-weight:600;">Estado:</dt>
            <dd><span class="badge badge--${a.estado === 'completada' ? 'complete' : 'pending'}">${a.estado}</span></dd>
            <dt style="font-weight:600;">Creada:</dt>
            <dd>${a.creada}</dd>
            <dt style="font-weight:600;">Última actualización:</dt>
            <dd>${a.actualizacion}</dd>
          </dl>
        </div>

        <div class="detail-card">
          <h2 class="detail-card__title">Resumen de Conformidad</h2>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-item__value">${a.resumen.total_controles}</div>
              <div class="stat-item__label">Total Controles</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="color: var(--color-success);">${a.resumen.conformes}</div>
              <div class="stat-item__label">Conformes</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="color: var(--color-danger);">${a.resumen.no_conformes}</div>
              <div class="stat-item__label">No Conformes</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="color: var(--color-warning);">${a.resumen.parcialmente_conformes}</div>
              <div class="stat-item__label">Parciales</div>
            </div>
          </div>
          <div style="margin-top: 1rem;">
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.3rem;">
              <span>Conformidad</span>
              <span>${porcentajeConformidad}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-bar__fill progress-bar__fill--${porcentajeConformidad >= 80 ? 'success' : porcentajeConformidad >= 60 ? 'warning' : 'danger'}" 
                   style="width: ${porcentajeConformidad}%;" 
                   role="progressbar" 
                   aria-valuenow="${porcentajeConformidad}" 
                   aria-valuemin="0" 
                   aria-valuemax="100"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Severidad -->
      <div class="detail-grid">
        <div class="detail-card">
          <h2 class="detail-card__title">Hallazgos por Severidad</h2>
          <div class="stats-grid">
            <div class="stat-item">
              <div class="stat-item__value" style="color: #a30000;">${severityCount.alta}</div>
              <div class="stat-item__label">Alta</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="color: #856404;">${severityCount.media}</div>
              <div class="stat-item__label">Media</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="color: #155724;">${severityCount.baja}</div>
              <div class="stat-item__label">Baja</div>
            </div>
          </div>
        </div>

        <div class="detail-card">
          <h2 class="detail-card__title">Resultados de Agentes</h2>
          <div class="agent-results">
            ${a.agentes.map(ag => `
              <div class="agent-card">
                <div class="agent-card__name">${ag.nombre}</div>
                <div class="agent-card__status">
                  Estado: <span class="badge badge--complete">${ag.estado}</span><br>
                  Controles evaluados: ${ag.controles_evaluados}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- Tabla de Hallazgos -->
      <div class="detail-card detail-card--full" style="margin-top: 0;">
        <h2 class="detail-card__title">Hallazgos</h2>
        <div class="table-container" role="region" aria-label="Tabla de hallazgos">
          <table class="table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Control</th>
                <th scope="col">Descripción</th>
                <th scope="col">Severidad</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              ${a.hallazgos.map((h, i) => `
                <tr>
                  <td>${i + 1}</td>
                  <td><strong>${h.control}</strong></td>
                  <td>${h.descripcion}</td>
                  <td><span class="badge badge--${h.severidad === 'alta' ? 'high' : h.severidad === 'media' ? 'medium' : 'low'}">${h.severidad}</span></td>
                  <td>${this.formatEstadoHallazgo(h.estado)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  formatEstadoHallazgo(estado) {
    const map = {
      'abierto': '<span class="badge badge--high">Abierto</span>',
      'en_remediacion': '<span class="badge badge--medium">En remediación</span>',
      'cerrado': '<span class="badge badge--complete">Cerrado</span>'
    };
    return map[estado] || estado;
  }
};
