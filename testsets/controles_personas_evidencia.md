# Evidencia de Controles de Personas (A.6) — ACME Corp

**Organizacion:** ACME Corp S.A. de C.V.
**Periodo de evaluacion:** Julio 2024 – Junio 2025
**Responsable:** Lic. Ana Martinez, Gerente de Recursos Humanos
**Fecha del documento:** 2025-06-18

---

## A.6.1 — Investigacion de Antecedentes (Screening)

### Proceso Documentado

Todos los candidatos a posiciones en ACME Corp son sometidos a verificacion de antecedentes antes de la contratacion. El proceso incluye:

1. Verificacion de identidad (INE/pasaporte)
2. Validacion de grado academico con institucion educativa
3. Verificacion de referencias laborales (ultimos 2 empleadores)
4. Consulta en buro de credito (solo para posiciones con manejo financiero)
5. Verificacion de antecedentes penales (constancia de no antecedentes)

### Evidencia Disponible

| Metrica | Valor | Observacion |
|---------|-------|-------------|
| Contrataciones en el periodo | 28 | 14 desarrollo, 8 soporte, 4 administracion, 2 seguridad |
| Investigaciones completadas | 26 | 92.8% de cumplimiento |
| Investigaciones pendientes | 2 | Contrataciones urgentes de diciembre 2024 |
| Hallazgos relevantes | 1 | Candidato descartado por falsificacion de titulo |
| Tiempo promedio de verificacion | 5 dias habiles | Dentro del SLA de 7 dias |

### Hallazgos

- **No conformidad menor:** 2 empleados del area de desarrollo fueron contratados en diciembre 2024 sin completar la verificacion de antecedentes debido a urgencia del proyecto. La verificacion se completo posteriormente (enero 2025) sin hallazgos negativos, pero el proceso no se siguio en el orden correcto.
- El proveedor de verificacion de antecedentes (VerificaMX) no tiene acuerdo de confidencialidad actualizado (vencio en septiembre 2024).

---

## A.6.2 — Terminos y Condiciones de Empleo

### Documentacion Contractual

Todos los contratos laborales incluyen las siguientes clausulas de seguridad:

- Clausula de confidencialidad (vigente durante y 2 anos despues de la relacion laboral)
- Clausula de propiedad intelectual (todo desarrollo durante horario laboral es propiedad de ACME Corp)
- Clausula de uso aceptable de recursos tecnologicos
- Reconocimiento de politicas de seguridad de la informacion
- Obligacion de reportar incidentes de seguridad
- Consecuencias por incumplimiento (amonestacion, suspension, rescision)

### Evidencia

| Tipo de contrato | Total | Con clausulas de seguridad | Cumplimiento |
|-----------------|-------|---------------------------|--------------|
| Empleados de planta | 95 | 95 | 100% |
| Contratistas temporales | 18 | 16 | 88.9% |
| Becarios/practicantes | 7 | 7 | 100% |

### Hallazgos

- **No conformidad menor:** 2 contratistas del proyecto "Migracion ERP" (contratados via outsourcing TechStaff) no firmaron el anexo de seguridad de informacion. La empresa de outsourcing argumenta que su propio NDA es suficiente, pero no cubre especificamente los requisitos del SGSI de ACME Corp.

---

## A.6.3 — Concientizacion, Educacion y Capacitacion en Seguridad

### Programa de Capacitacion 2024-2025

| Actividad | Frecuencia | Audiencia | Completado | Meta |
|-----------|-----------|-----------|------------|------|
| Induccion de seguridad (nuevos ingresos) | Continua | Nuevos empleados | 28/28 | 100% |
| Capacitacion anual de seguridad (e-learning) | Anual | Todos | 98/120 | 95% |
| Simulacion de phishing | Trimestral | Todos | 4/4 campanas | 100% |
| Capacitacion especializada (OWASP, SecOps) | Semestral | Desarrollo + TI | 22/35 | 80% |
| Taller de clasificacion de informacion | Anual | Gerentes | 8/12 | 90% |
| Certificacion ISO 27001 Lead Auditor | Unica | Equipo Seguridad | 2/3 | 100% |

### Resultados de Simulaciones de Phishing

| Campana | Fecha | Correos enviados | Clicks en enlace | Credenciales ingresadas | Reportes correctos |
|---------|-------|-----------------|------------------|------------------------|-------------------|
| Q3 2024 | 2024-08-15 | 120 | 18 (15%) | 7 (5.8%) | 34 (28.3%) |
| Q4 2024 | 2024-11-20 | 118 | 14 (11.9%) | 5 (4.2%) | 45 (38.1%) |
| Q1 2025 | 2025-02-12 | 120 | 11 (9.2%) | 3 (2.5%) | 52 (43.3%) |
| Q2 2025 | 2025-05-18 | 119 | 9 (7.6%) | 2 (1.7%) | 61 (51.3%) |

**Tendencia positiva:** Reduccion del 71% en credenciales comprometidas y aumento del 79% en reportes correctos entre Q3 2024 y Q2 2025.

### Hallazgos

- **Observacion:** La capacitacion anual general tiene 81.7% de completitud (98/120), por debajo de la meta de 95%. Los 22 empleados pendientes son principalmente del area de operaciones y soporte en campo.
- **Observacion:** La capacitacion especializada en desarrollo seguro solo alcanza 62.8% (22/35 del equipo tecnico). No se ha cubierto al equipo de QA ni a los DevOps engineers.
- **Mejora identificada:** No existe un modulo especifico de capacitacion para trabajo remoto seguro, a pesar de que el 40% de los empleados trabajan en modalidad hibrida.

---

## A.6.4 — Proceso Disciplinario

### Procedimiento

El proceso disciplinario por violaciones a la seguridad de la informacion sigue una escala progresiva:

1. **Primera instancia (leve):** Amonestacion verbal con registro en expediente
2. **Segunda instancia o falta moderada:** Amonestacion escrita con plan de accion correctiva
3. **Falta grave:** Suspension sin goce de sueldo (3-15 dias) + capacitacion obligatoria
4. **Falta critica o reincidencia:** Rescision de contrato (Art. 47 LFT fracciones aplicables)

### Registro de Acciones Disciplinarias (Periodo)

| Fecha | Tipo | Area | Descripcion | Accion Tomada |
|-------|------|------|-------------|---------------|
| 2024-08-05 | Leve | Soporte | Compartio contrasena con companero para cubrir vacaciones | Amonestacion verbal + re-capacitacion |
| 2024-10-12 | Moderada | Desarrollo | Subio codigo fuente de proyecto cliente a repositorio personal publico | Amonestacion escrita + eliminacion del repo + NDA reforzado |
| 2024-11-18 | Grave | Ventas | Copio base de datos de clientes a USB personal previo a renuncia | Rescision inmediata + accion legal + notificacion a clientes |
| 2025-01-30 | Leve | Administracion | Dejo documentos confidenciales sobre escritorio al salir (violacion de escritorio limpio) | Amonestacion verbal |
| 2025-03-15 | Moderada | TI | Instalo software no autorizado (servidor de juegos) en equipo corporativo | Amonestacion escrita + remocion de privilegios administrativos locales |

### Hallazgos

- El proceso disciplinario esta documentado y se aplica consistentemente.
- No se identificaron brechas significativas en la aplicacion del proceso.

---

## A.6.5 — Responsabilidades tras la Finalizacion o Cambio de Empleo

### Proceso de Offboarding

Checklist de seguridad al terminar relacion laboral:

| Paso | Responsable | SLA | Cumplimiento |
|------|-------------|-----|--------------|
| Desactivacion de cuentas de red y correo | TI | Mismo dia | 85% |
| Revocacion de acceso VPN | TI | Mismo dia | 90% |
| Recuperacion de equipo (laptop, movil) | TI + RRHH | 3 dias | 95% |
| Revocacion de accesos a servicios cloud | TI | Mismo dia | 78% |
| Entrevista de salida (aspectos de seguridad) | RRHH | 5 dias | 70% |
| Devolucion de tarjeta de acceso fisico | Seguridad Fisica | Mismo dia | 92% |
| Recordatorio de obligaciones post-empleo (NDA) | Legal | 5 dias | 100% |

### Estadisticas del Periodo

- Bajas totales en el periodo: 15 (9 renuncias, 4 fin de contrato, 2 rescisiones)
- Offboarding completo en SLA: 11/15 (73.3%)
- Tiempo promedio de desactivacion de accesos: 1.8 dias

### Hallazgos

- **No conformidad menor:** En 4 de 15 bajas, los accesos a servicios cloud (AWS Console, GitHub, Jira) no fueron revocados el mismo dia. En un caso extremo, la cuenta de AWS de un ex-desarrollador permanecio activa por 23 dias despues de su salida.
- **No conformidad menor:** La entrevista de salida con componente de seguridad solo se realizo en el 70% de los casos. No hay evidencia de que se hayan cubierto temas de seguridad en las entrevistas realizadas por RRHH sin participacion del equipo de seguridad.

---

## A.6.6 — Acuerdos de Confidencialidad o No Divulgacion

### Inventario de NDAs

| Tipo | Firmados | Vigentes | Vencidos | Pendientes |
|------|----------|----------|----------|-----------|
| Empleados de planta | 95 | 95 | 0 | 0 |
| Contratistas | 18 | 15 | 3 | 0 |
| Proveedores criticos | 12 | 10 | 2 | 0 |
| Ex-empleados (post-empleo) | 42 | 38 | 4 | 0 |

### Hallazgos

- **Observacion:** 3 NDAs de contratistas y 2 de proveedores estan vencidos y no han sido renovados. Los contratistas afectados siguen con acceso activo a sistemas.
- Los NDAs de ex-empleados tienen vigencia de 2 anos post-empleo. No existe un mecanismo de seguimiento para verificar cumplimiento una vez que el periodo expira.

---

## A.6.7 — Trabajo Remoto

### Politica de Trabajo Remoto

- Modalidad hibrida: 3 dias oficina / 2 dias remoto (aprobada desde enero 2024)
- Empleados 100% remotos: 12 (ubicaciones fuera de las 3 ciudades sede)
- Requisitos minimos para trabajo remoto:
  - VPN corporativa activa en todo momento
  - Equipo proporcionado por la empresa (no se permite BYOD para acceso a produccion)
  - Ambiente fisico adecuado (espacio privado, sin acceso visual de terceros)
  - Conexion a internet con minimo 20 Mbps
  - Actualizaciones de sistema operativo al dia

### Evaluacion de Cumplimiento

| Control de Trabajo Remoto | Implementado | Verificado | Observacion |
|--------------------------|--------------|-----------|-------------|
| VPN obligatoria | Si | Parcial | Logs muestran 8 conexiones directas sin VPN en mayo 2025 |
| Cifrado de disco completo | Si | Si | BitLocker/FileVault habilitado en 100% de equipos |
| Antivirus/EDR activo | Si | Si | CrowdStrike Falcon en todos los endpoints |
| Bloqueo automatico (5 min) | Si | Parcial | No verificable en equipos remotos sin MDM completo |
| Prohibicion de redes publicas sin VPN | Si (politica) | No | No existe control tecnico que lo impida |
| Backup local prohibido | Si (politica) | No | No existe DLP que detecte copias locales |

### Hallazgos

- **No conformidad menor:** No existe verificacion tecnica de que los empleados remotos utilicen la VPN en todo momento. Los logs muestran accesos directos a servicios cloud desde IPs residenciales sin pasar por la VPN corporativa.
- **Observacion:** No se ha realizado ninguna auditoria fisica del espacio de trabajo remoto de los empleados. La auto-declaracion del empleado es el unico control.
- **Mejora identificada:** Se recomienda implementar MDM (Mobile Device Management) completo para verificar cumplimiento de controles en endpoints remotos.

---

## A.6.8 — Reporte de Eventos de Seguridad de la Informacion

### Canales de Reporte

- Canal de Slack #seguridad-reportes (disponible 24/7)
- Correo electronico: incidentes@acme-corp.com
- Extension telefonica: 5555 (horario laboral)
- Formulario anonimo en intranet para denuncias

### Estadisticas de Reporte

| Metrica | Q3 2024 | Q4 2024 | Q1 2025 | Q2 2025 | Tendencia |
|---------|---------|---------|---------|---------|-----------|
| Reportes recibidos | 12 | 18 | 22 | 28 | Creciente (+133%) |
| Reportes validos (incidentes reales) | 4 | 6 | 8 | 7 | Estable |
| Falsos positivos | 8 | 12 | 14 | 21 | Creciente |
| Tiempo promedio de reporte (horas) | 18 | 12 | 8 | 5 | Mejorando |
| Reportes anonimos | 1 | 2 | 3 | 4 | Creciente |

### Hallazgos

- **Positivo:** El incremento en reportes indica mayor concientizacion entre los empleados. El tiempo de reporte se ha reducido significativamente.
- **Observacion:** El alto ratio de falsos positivos (75% en Q2 2025) sugiere que los empleados necesitan mejor guia sobre que constituye un evento reportable vs. operacion normal.
- **Positivo:** El canal anonimo esta siendo utilizado, lo que indica confianza en el sistema de reporte.

---

## Resumen de Hallazgos por Control

| Control | Estado | No Conformidades | Observaciones |
|---------|--------|-----------------|---------------|
| A.6.1 Screening | Parcialmente conforme | 1 menor | 1 |
| A.6.2 Terminos de empleo | Parcialmente conforme | 1 menor | 0 |
| A.6.3 Concientizacion | Parcialmente conforme | 0 | 3 |
| A.6.4 Proceso disciplinario | Conforme | 0 | 0 |
| A.6.5 Finalizacion de empleo | Parcialmente conforme | 2 menores | 0 |
| A.6.6 Confidencialidad | Parcialmente conforme | 0 | 2 |
| A.6.7 Trabajo remoto | Parcialmente conforme | 1 menor | 2 |
| A.6.8 Reporte de eventos | Conforme | 0 | 1 |

**Total:** 5 no conformidades menores, 9 observaciones de mejora.

---

*Documento clasificado como: INTERNO*
*Preparado para revision del Comite de Seguridad de la Informacion — Sesion del 25 de junio 2025*
