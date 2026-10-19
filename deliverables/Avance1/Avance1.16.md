# Avance 1 — Base de Conocimiento del Proyecto

**Equipo:** #16
**Fecha:** 12 de mayo de 2026

Este documento describe el contenido de cada subcarpeta dentro de `knowledge-base/` y explica cómo cada conjunto de materiales puede ser aprovechado para el desarrollo del agente de auditoría ISO 27001.

---

## Resumen por tipo de documento

| Sección | `.pdf` | `.docx` | `.yaml` | **Total** |
|---|:-:|:-:|:-:|:-:|
| `audit-examples` | 6 | 1 | — | **7** |
| `audit-methodology` | 4 | — | — | **4** |
| `ciso-assistant-community` | — | — | 4 | **4** |
| `iso27001` | 1 | — | — | **1** |
| `sponsor-documents` | 6 | 1 | — | **7** |
| **Total** | **17** | **2** | **4** | **23** |

---

## 1. `audit-examples`

Contiene 7 reportes reales de auditoría ISO 27001 obtenidos de fuentes públicas. Los documentos incluyen auditorías de precertificación, vigilancia anual, recertificación y evaluaciones iniciales. Algunos están redactados o anonimizados.

**Archivos:**

- `2017_iso-iec_27001_isms_precertification_audit_-_january_2018.pdf` — Auditoría de precertificación del ISMS de la Ciudad de Atlanta (Experis U.S., 2018).
- `Independent-Press-Standards-Organisation-ISO-27001_2013-Remote-Audit-Report-30112023-CS-signed.pdf` — Auditoría remota Etapa 2 de IPSO contra ISO 27001:2013 (noviembre 2023, cero no conformidades).
- `redacted-true-iso-27001_audit-report.pdf` — Primer reporte de vigilancia y transición a ISO 27001:2022 de True Sustainability, con datos sensibles redactados.
- `hcpc-audit-report-2018.pdf` — Recertificación BSI del Health & Care Professions Council, auditoría presencial de 4 días.
- `anonimized-iso-27001-initial-assessment-report-2024.pdf` — Evaluación inicial ISO 27001 de UnderDefense con identidad del cliente anonimizada.
- `Soterion-ISO-27001-Certificate-1.pdf` — Reporte de evaluación del ISMS de Soterion Technologies (Pty) Ltd.
- `06100-FO8-Audit-Report_27001-2022_v4.0.docx` — Formulario oficial de reporte de auditoría ISO 27001:2022 utilizado por MSECB.

**Uso para el agente:** Estos reportes sirven como datos de entrenamiento y referencia para que el agente comprenda la estructura real de un reporte de auditoría, los tipos de hallazgos, la forma en que se documentan no conformidades y observaciones, y el nivel de detalle esperado en cada sección. Permiten al agente generar borradores de reportes con un formato y lenguaje alineado a la práctica real.

---

## 2. `audit-methodology`

Contiene documentos normativos y de referencia sobre cómo planificar y ejecutar auditorías de sistemas de gestión. Incluye materiales en español aplicables al contexto latinoamericano.

**Archivos:**

- `2.1_requisitos_norma_iso_19011-2011.pdf` — Requisitos de la norma ISO 19011:2011, guía internacional para auditar sistemas de gestión.
- `ieeg-resultados-de-auditoria-en-madurez-ti-v1.2-2015.pdf` — Modelo de resultados de auditoría en madurez de TI del IEEG (v1.2, 2015).
- `planeacion-de-auditoria-prep-v1.1-2015.pdf` — Documento de planeación de auditoría con estructura de preparación.
- `plexus-diagnostico_pss_iaft16949-2018.pdf` — Diagnóstico de sistema de gestión de Plexus, útil como referencia de metodología de diagnóstico previo a certificación.

**Uso para el agente:** Estos documentos definen el proceso que el agente debe replicar: cómo estructurar un plan de auditoría, qué criterios usar para evaluar madurez, y cómo interpretar y presentar resultados. Fundamentan la lógica de razonamiento del agente al momento de generar planes de auditoría o evaluar evidencias.

---

## 3. `ciso-assistant-community`

Contiene archivos YAML estructurados con la representación legible por máquina de cuatro normas internacionales ISO, descargados del proyecto de código abierto [CISO Assistant Community](https://github.com/intuitem/ciso-assistant-community) de intuitem.

**Archivos:**

- `iso27001-2022.yaml` — Cláusulas 4–10 y Anexo A completo de ISO/IEC 27001:2022 (93 controles en 4 categorías). Incluye traducciones al español, francés, alemán, chino y otros idiomas.
- `iso27001-2013.yaml` — Cláusulas 4–10 y Anexo A de ISO/IEC 27001:2013 (114 controles en 14 dominios). Base para análisis de brechas entre ediciones.
- `iso22301-2019.yaml` — Requisitos de ISO 22301:2019 (continuidad de negocio), referenciada directamente en controles del Anexo A de ISO 27001.
- `iso42001-2023.yaml` — Requisitos y controles de ISO 42001:2023 (gestión de sistemas de inteligencia artificial), con modelo de madurez 0–5.

**Uso para el agente:** Son la columna vertebral del conocimiento normativo del agente. Cada `ref_id` de cláusula o control puede usarse como clave de referencia para mapear evidencias del cliente, identificar brechas, asignar puntajes de madurez y generar recomendaciones. Al estar en formato YAML, pueden cargarse directamente como contexto estructurado o integrarse en una base de datos vectorial.

---

## 4. `iso27001`

Contiene el texto completo de la norma ISO/IEC 27001 en su edición 2013 en formato PDF.

**Archivos:**

- `iso-iec-27001-2013-en.pdf` — Texto oficial de la norma ISO/IEC 27001:2013 en inglés.

**Uso para el agente:** Complementa los archivos YAML de `ciso-assistant-community` al proporcionar el texto normativo completo para consultas que requieran mayor precisión o contexto que el resumen estructurado. Puede usarse para alimentar un pipeline de RAG (Retrieval-Augmented Generation) que permita al agente citar requisitos específicos con exactitud.

---

## 5. `sponsor-documents`

Contiene documentos internos de la organización patrocinadora del proyecto, principalmente políticas y guías de seguridad de la información vigentes. Son el contexto real sobre el que se aplicará el agente.

**Archivos:**

- `politica-de-seguridad-de-la-informacion-15nov2024.pdf` — Política principal de seguridad de la información (noviembre 2024).
- `politica-de-colaboracion-digital-05jul2024.pdf` — Política de colaboración digital (julio 2024).
- `politicas-seguridad-software-tec-2026.docx` — Políticas de seguridad de software (2026).
- `actualiza-dispositivos-y-apps.pdf` — Guía sobre actualización de dispositivos y aplicaciones.
- `almacenar-compartir.pdf` — Guía sobre almacenamiento y compartición segura de información.
- `dispositivos-personales.pdf` — Guía de uso de dispositivos personales (BYOD).
- `redes-sociales.pdf` — Guía de uso de redes sociales.
- `respaldo.pdf` — Guía de respaldo de información.

**Uso para el agente:** Representan la evidencia documental real del cliente. El agente puede analizar estas políticas y compararlas contra los controles del Anexo A de ISO 27001 para identificar brechas, generar hallazgos y proponer recomendaciones contextualizadas a la organización. Son el insumo principal para simular una auditoría real sobre el patrocinador.
