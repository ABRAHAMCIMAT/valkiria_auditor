/**
 * Landing Page - Página de inicio
 */
const LandingPage = {
  render() {
    return `
      <section class="hero" aria-labelledby="hero-title">
        <div class="hero__container">
          <div class="hero__content">
            <h1 id="hero-title" class="hero__title">Auditor Lead</h1>
            <p class="hero__description">
              Es una plataforma que te permitirá acelerar tus ciclos de evaluación de aplicaciones 
              y servicios en cumplimiento de la norma ISO 27001 con un conjunto de artefactos, 
              reportes y análisis agilizando los ciclos de evaluación y certificación.
            </p>
          </div>
          <div class="hero__image">
            <img src="assets/images/iso_27001_lead_auditor.svg" alt="ISO 27001 Lead Auditor" loading="lazy">
          </div>
        </div>
      </section>

      <div class="landing-sections">
        <article class="landing-card" aria-labelledby="card-auditorias">
          <h2 id="card-auditorias" class="landing-card__title">Auditorias</h2>
          <p class="landing-card__description">
            En esta sección podrás dar seguimiento a los proyectos de auditoría para una o más 
            cargas de trabajo, por empresa o por aplicación. Gestiona el ciclo completo de 
            auditoría con agentes de IA especializados.
          </p>
          <a href="#/auditorias" class="btn btn--auditorias">Auditorias</a>
        </article>

        <article class="landing-card" aria-labelledby="card-evaluaciones">
          <h2 id="card-evaluaciones" class="landing-card__title">Evaluaciones</h2>
          <p class="landing-card__description">
            En esta sección se realiza el seguimiento de las evaluaciones. Aquí podrás cargar 
            los recursos de código, endpoints y conexiones con fuentes tecnológicas para la 
            automatización de tus evaluaciones.
          </p>
          <a href="#/evaluaciones" class="btn btn--evaluaciones">Evaluaciones</a>
        </article>
      </div>
    `;
  },

  afterRender() {
    // No dynamic behavior needed for landing
  }
};
