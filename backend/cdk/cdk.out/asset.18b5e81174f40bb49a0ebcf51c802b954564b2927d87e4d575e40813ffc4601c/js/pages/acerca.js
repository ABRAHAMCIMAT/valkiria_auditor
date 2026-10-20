/**
 * Acerca de Page - Información del proyecto y equipo
 */
const AcercaPage = {
  render() {
    return `
      <div class="page-header">
        <div class="page-header__container">
          <h1 class="page-header__title">Acerca de</h1>
          <p class="page-header__subtitle">Conoce más sobre Auditor Lead y nuestro equipo</p>
        </div>
      </div>

      <div class="page-content">
        <section class="about-section" aria-labelledby="about-project">
          <h2 id="about-project" class="about-section__title">El Proyecto</h2>
          <p class="about-section__text">
            <strong>Auditor Lead</strong> es una plataforma innovadora diseñada para acelerar los ciclos de 
            evaluación de aplicaciones y servicios en cumplimiento de la norma ISO/IEC 27001. 
            Mediante el uso de agentes de inteligencia artificial especializados, automatiza el proceso 
            de auditoría y evaluación, generando artefactos, reportes y análisis que agilizan los ciclos 
            de evaluación y certificación.
          </p>
        </section>

        <section class="about-section" aria-labelledby="about-features">
          <h2 id="about-features" class="about-section__title">Características Principales</h2>
          <div class="about-section__text">
            <ul style="list-style:none; padding:0;">
              <li style="padding:0.5rem 0; border-bottom:1px solid #eee;">
                🤖 <strong>Agentes de IA Especializados</strong> — Evaluación automatizada de controles organizacionales, 
                de personas, físicos y tecnológicos.
              </li>
              <li style="padding:0.5rem 0; border-bottom:1px solid #eee;">
                📋 <strong>Soporte Multi-Versión</strong> — Compatible con ISO 27001:2022 (93 controles, 4 dominios) 
                e ISO 27001:2013 (114 controles, 14 dominios).
              </li>
              <li style="padding:0.5rem 0; border-bottom:1px solid #eee;">
                🔄 <strong>Múltiples Frameworks</strong> — Integración con Strands Agents, LangGraph y CrewAI 
                para la ejecución de auditorías.
              </li>
              <li style="padding:0.5rem 0; border-bottom:1px solid #eee;">
                📊 <strong>Reportes y Análisis</strong> — Generación automática de hallazgos, métricas de conformidad 
                y recomendaciones de remediación.
              </li>
              <li style="padding:0.5rem 0;">
                🔗 <strong>Integraciones</strong> — Carga de código fuente, endpoints y conexiones con fuentes 
                tecnológicas para evaluación automatizada.
              </li>
            </ul>
          </div>
        </section>

        <section class="about-section" aria-labelledby="about-tech">
          <h2 id="about-tech" class="about-section__title">Tecnología</h2>
          <p class="about-section__text">
            Auditor Lead está construido sobre una arquitectura moderna que combina servicios en la nube 
            de AWS con agentes de IA avanzados. El backend utiliza Amazon Bedrock AgentCore para orquestar 
            múltiples agentes especializados que evalúan diferentes dominios de la norma ISO 27001.
          </p>
          <div style="margin-top:1rem; display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:1rem;">
            <div class="stat-item">
              <div class="stat-item__value" style="font-size:1.2rem;">☁️</div>
              <div class="stat-item__label">AWS Cloud</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="font-size:1.2rem;">🧠</div>
              <div class="stat-item__label">Bedrock AgentCore</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="font-size:1.2rem;">🐍</div>
              <div class="stat-item__label">Python Backend</div>
            </div>
            <div class="stat-item">
              <div class="stat-item__value" style="font-size:1.2rem;">⚡</div>
              <div class="stat-item__label">Lambda Functions</div>
            </div>
          </div>
        </section>

        <section class="about-section" aria-labelledby="about-team">
          <h2 id="about-team" class="about-section__title">Equipo</h2>
          <p class="about-section__text" style="margin-bottom:1rem;">
            Proyecto integrador desarrollado como parte del programa de Maestría en Inteligencia Artificial 
            Aplicada.
          </p>
          <div class="team-grid">
            <div class="team-member">
              <div class="team-member__avatar">E16</div>
              <div class="team-member__name">Equipo 16</div>
              <div class="team-member__role">Proyecto Integrador MNA</div>
            </div>
          </div>
        </section>
      </div>
    `;
  },

  afterRender() {
    // No dynamic behavior needed
  }
};
