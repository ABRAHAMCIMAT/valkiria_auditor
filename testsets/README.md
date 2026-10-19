# Test Datasets — Sistema Multi-Agente ISO 27001

Datos sinteticos de prueba para validar el pipeline completo del sistema de auditoria ISO 27001:2022. Todos los archivos son compatibles con el frontend y los formatos que procesa el backend.

## Organizacion Simulada

**ACME Corp S.A. de C.V.** — empresa de tecnologia/desarrollo de software con 120 empleados en 3 ubicaciones (CDMX, Guadalajara, Monterrey). La organizacion tiene un SGSI parcialmente maduro con brechas deliberadas para que los agentes detecten no conformidades.

## Archivos

| Archivo | Formato | Tamano | Dominio ISO | Proposito |
|---------|---------|--------|-------------|-----------|
| `sonarqube_report.json` | JSON | ~15 KB | A.8 Tecnologicos | 18 vulnerabilidades SAST (6 criticas/altas) |
| `owasp_zap_report.xml` | XML | ~18 KB | A.8 Tecnologicos | 11 alertas DAST (4 altas, 5 medias) |
| `dependency_check_report.csv` | CSV | ~5 KB | A.8 Tecnologicos | 23 dependencias vulnerables con CVEs |
| `politicas_seguridad_informacion.md` | Markdown | ~14 KB | A.5 Organizacionales | Politicas, roles, clasificacion, proveedores, BCP |
| `controles_personas_evidencia.md` | Markdown | ~12 KB | A.6 Personas | Screening, capacitacion, offboarding, trabajo remoto |
| `seguridad_fisica_evaluacion.md` | Markdown | ~16 KB | A.7 Fisicos | 3 ubicaciones, CCTV, perimetros, mantenimiento |
| `iso27001_controls_assessment.json` | JSON | ~12 KB | Todos (A.5-A.8) | 28 controles en formato CISO Assistant |
| `registro_riesgos.yaml` | YAML | ~12 KB | Todos (A.5-A.8) | 13 riesgos con tratamiento (ISO 27005) |

## Como Usar

### Opcion 1: Carga Individual via Frontend

1. Abrir el frontend desplegado (URL de CloudFront)
2. Ir a la seccion **Auditorias** > **Nueva Auditoria**
3. Seleccionar **ISO/IEC 27001:2022**
4. Seleccionar framework: **Strands Agents** (u otro disponible)
5. En "Datos de evaluacion", usar la pestana **Archivos individuales**
6. Arrastrar o seleccionar los 8 archivos de este directorio
7. En "Contexto organizacional", escribir:
   ```
   ACME Corp S.A. de C.V. Empresa de tecnologia con 120 empleados en 3 ubicaciones
   (CDMX, Guadalajara, Monterrey). Desarrollo de software para clientes enterprise.
   SGSI implementado desde 2023, certificacion ISO 27001 vigente con auditoria de
   vigilancia proxima en septiembre 2025.
   ```
8. Clic en **Crear y ejecutar auditoria**

### Opcion 2: Carga via ZIP

1. Comprimir todos los archivos (sin el README):
   ```bash
   cd testsets
   zip acme_corp_auditoria.zip \
     sonarqube_report.json \
     owasp_zap_report.xml \
     dependency_check_report.csv \
     politicas_seguridad_informacion.md \
     controles_personas_evidencia.md \
     seguridad_fisica_evaluacion.md \
     iso27001_controls_assessment.json \
     registro_riesgos.yaml
   ```
2. En el frontend, usar la pestana **Archivo .zip** y subir `acme_corp_auditoria.zip`

### Opcion 3: Carga via API (presigned URL)

```bash
# Obtener URL prefirmada
curl -X POST https://<API_ENDPOINT>/upload/presigned-url \
  -H "Content-Type: application/json" \
  -d '{"file_name": "sonarqube_report.json", "content_type": "application/json"}'

# Subir archivo con la URL devuelta
curl -X PUT "<upload_url>" \
  -H "Content-Type: application/json" \
  --data-binary @testsets/sonarqube_report.json
```

## Que Debe Detectar el Sistema

### Agente de Controles Organizacionales (A.5)
- Revision de politica vencida (3 meses de retraso)
- 8 cuentas con privilegios excesivos sin remediar
- Proveedor sin evidencia de destruccion certificada
- BCP/DR no probado para ERP
- Incidente P1 que excedio SLA

### Agente de Controles de Personas (A.6)
- 2 contrataciones sin verificacion previa completada
- Capacitacion al 81.7% (meta 95%)
- Offboarding incompleto (73.3% en SLA)
- Cuenta AWS activa 23 dias post-salida
- 40% laptops sin MDM

### Agente de Controles Fisicos (A.7)
- Camara fuera de servicio 43 dias (MTY)
- 5 tarjetas de acceso huerfanas
- Tasa de violaciones escritorio limpio 18.3%
- Impresoras sin borrado de memoria
- UPS faltante en MTY

### Agente de Controles Tecnologicos (A.8)
- SQL Injection, XSS almacenado, SSRF (SonarQube)
- IDOR critico en API de reportes (ZAP)
- JWT acepta algoritmo 'none'
- MD5 para passwords, TLS 1.0/1.1 habilitado
- 23 dependencias con CVEs (3 criticas: RCE)
- Upload sin validacion permite ejecucion de codigo

### Orquestador (Consolidacion)
- 5 no conformidades mayores
- 13 no conformidades menores
- 13 riesgos identificados (2 criticos, 5 altos)
- Madurez promedio: 2.5/5 (entre Repetible y Definido)
- Riesgo residual promedio: 9.1 (en el limite del apetito de riesgo)

## Notas Tecnicas

- Todos los datos son **ficticios**. Los CVEs referenciados son reales pero las versiones y hallazgos son simulados para el escenario de prueba.
- Los archivos JSON y YAML son compatibles con el parser del Lambda `eda_analysis` (formato CISO Assistant con campos `ref_id`, `domain`, `description`).
- El CSV usa headers estandar de OWASP Dependency Check.
- El XML sigue el esquema de reporte de OWASP ZAP 2.15.
- Los archivos Markdown contienen texto suficiente para chunking semantico efectivo (~500-2000 tokens por seccion).
