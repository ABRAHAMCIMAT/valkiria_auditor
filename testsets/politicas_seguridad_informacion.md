# Politicas de Seguridad de la Informacion — ACME Corp

**Organizacion:** ACME Corp S.A. de C.V.
**Sector:** Tecnologia / Desarrollo de Software
**Empleados:** 120
**Ubicaciones:** Ciudad de Mexico (Corporativo), Guadalajara (Centro de Desarrollo), Monterrey (Soporte)
**Fecha de aprobacion:** 2024-03-15
**Version:** 2.1
**Aprobado por:** Comite de Seguridad de la Informacion
**Proxima revision:** 2025-03-15

---

## 1. Politica General de Seguridad de la Informacion (A.5.1)

### 1.1 Declaracion de la Direccion

La Alta Direccion de ACME Corp se compromete a proteger los activos de informacion de la organizacion, garantizando su confidencialidad, integridad y disponibilidad. La seguridad de la informacion es un pilar estrategico para la continuidad del negocio y la confianza de nuestros clientes.

### 1.2 Alcance

Esta politica aplica a:
- Todos los empleados, contratistas y terceros con acceso a sistemas de informacion
- Todos los activos de informacion en formato digital y fisico
- Todas las ubicaciones de la organizacion y trabajo remoto
- Servicios en la nube (AWS, Azure) utilizados por la organizacion

### 1.3 Objetivos de Seguridad

1. Proteger la informacion de clientes y datos personales conforme a LFPDPPP
2. Mantener disponibilidad de servicios criticos al 99.5% mensual
3. Cumplir con requisitos contractuales de seguridad de clientes enterprise
4. Reducir incidentes de seguridad en un 30% anual respecto al periodo anterior

---

## 2. Roles y Responsabilidades (A.5.2, A.5.4)

### 2.1 Comite de Seguridad de la Informacion

| Rol | Responsable | Responsabilidades |
|-----|-------------|-------------------|
| Director de Seguridad (CISO) | Ing. Maria Lopez | Estrategia, presupuesto, reporte a Direccion |
| Oficial de Cumplimiento | Lic. Carlos Ruiz | Normatividad, auditorias, relacion con reguladores |
| Lider Tecnico de Seguridad | Ing. Roberto Sanchez | Arquitectura, herramientas, respuesta a incidentes |
| Representante de RRHH | Lic. Ana Martinez | Capacitacion, sanciones, procesos de personal |
| Representante Legal | Lic. Fernando Torres | Contratos, propiedad intelectual, datos personales |

### 2.2 Responsabilidades Generales

- **Todos los empleados:** Cumplir politicas, reportar incidentes, completar capacitacion anual
- **Gerentes de area:** Asegurar cumplimiento en su equipo, aprobar accesos, clasificar informacion
- **Equipo de TI:** Implementar controles tecnicos, monitorear, parchar sistemas
- **Alta Direccion:** Proveer recursos, revisar desempeno del SGSI, aprobar politicas

---

## 3. Clasificacion de la Informacion (A.5.12, A.5.13)

### 3.1 Niveles de Clasificacion

| Nivel | Descripcion | Ejemplos | Controles Requeridos |
|-------|-------------|----------|---------------------|
| Confidencial | Dano severo si se divulga | Codigo fuente, datos financieros, PII de clientes | Cifrado en transito y reposo, acceso minimo, DLP |
| Interno | Solo para uso organizacional | Procesos internos, organigramas, minutas | Control de acceso, no compartir externamente |
| Publico | Disponible sin restriccion | Material de marketing, sitio web publico | Integridad verificable |

### 3.2 Etiquetado

- Documentos digitales: encabezado con nivel de clasificacion
- Correos electronicos: prefijo [CONFIDENCIAL] o [INTERNO] en asunto
- Documentos fisicos: sello en cada pagina
- Repositorios: etiquetas en README y .classification file

### 3.3 Manejo segun Clasificacion

**Confidencial:**
- Cifrado AES-256 en reposo, TLS 1.3 en transito
- Acceso solo por necesidad de conocer (need-to-know)
- Registro de accesos con retencion de 2 anos
- Destruccion segura: borrado criptografico o destruccion fisica

**Interno:**
- Almacenamiento en sistemas corporativos aprobados
- No almacenar en dispositivos personales sin cifrado
- Compartir solo mediante canales corporativos autorizados

---

## 4. Control de Acceso (A.5.15, A.5.16, A.5.17, A.5.18)

### 4.1 Principios

- Minimo privilegio: acceso solo a lo necesario para la funcion
- Separacion de funciones: ningun usuario controla un proceso critico completo
- Necesidad de conocer: acceso a informacion solo cuando es requerido para la tarea

### 4.2 Gestion de Identidades

- Identidad unica por persona (no se permiten cuentas compartidas)
- Formato de usuario: primera inicial + apellido (ej: mlopez)
- Cuentas de servicio: documentadas, con propietario asignado, rotacion trimestral de credenciales
- Desactivacion automatica tras 90 dias de inactividad

### 4.3 Autenticacion

- Contrasenas: minimo 12 caracteres, complejidad (mayusculas, minusculas, numeros, simbolos)
- MFA obligatorio para: VPN, correo electronico, sistemas criticos, acceso administrativo
- Bloqueo de cuenta tras 5 intentos fallidos (desbloqueo por Service Desk)
- Cambio obligatorio cada 90 dias para cuentas privilegiadas
- Prohibido reutilizar las ultimas 12 contrasenas

### 4.4 Revision de Accesos

- Trimestral: revision de accesos privilegiados por el CISO
- Semestral: revision de todos los accesos por gerentes de area
- Inmediata: revocacion al termino de relacion laboral (mismo dia)

**Hallazgo pendiente:** La ultima revision trimestral (Q4 2024) identifico 8 cuentas con privilegios excesivos que no han sido remediadas. 3 cuentas de ex-empleados permanecieron activas por 15-30 dias despues de su baja.

---

## 5. Seguridad en las Operaciones (A.5.23, A.5.26, A.5.37)

### 5.1 Gestion de Cambios

- Todo cambio en produccion requiere RFC (Request for Change) aprobado
- Aprobacion por Change Advisory Board (CAB) para cambios de alto riesgo
- Ventana de mantenimiento: domingos 02:00-06:00 CST
- Rollback plan obligatorio para cada cambio

### 5.2 Gestion de Vulnerabilidades

- Escaneo semanal de infraestructura con Nessus
- Escaneo de codigo en cada PR con SonarQube
- Pruebas de penetracion anuales por tercero independiente
- SLA de remediacion:
  - Criticas: 24 horas
  - Altas: 7 dias
  - Medias: 30 dias
  - Bajas: 90 dias

**Hallazgo pendiente:** El escaneo de vulnerabilidades del 15 de junio 2025 identifico 18 vulnerabilidades criticas y altas en el portal SGSI que exceden el SLA de remediacion. Ver reporte SonarQube adjunto.

### 5.3 Respaldo de Informacion

- Bases de datos: respaldo completo diario, incremental cada 6 horas
- Codigo fuente: repositorios Git con replica en 2 regiones AWS
- Documentos: sincronizacion con versionado en S3
- Prueba de restauracion: mensual para sistemas criticos
- Retencion: 30 dias operacional, 1 ano archivo, 7 anos legal/regulatorio

### 5.4 Registro y Monitoreo

- Logs centralizados en CloudWatch con retencion de 1 ano
- Alertas automaticas para: intentos de autenticacion fallidos (>5), acceso fuera de horario, cambios de privilegios, transferencias de datos >100MB
- Revision semanal de logs por el equipo de seguridad
- Correlacion de eventos con reglas SIEM basicas

**Hallazgo pendiente:** No se ha implementado un SIEM completo. La correlacion actual es manual y basada en reglas de CloudWatch, lo cual es insuficiente para deteccion avanzada de amenazas.

---

## 6. Seguridad en las Comunicaciones (A.5.14)

### 6.1 Transferencia de Informacion

- Informacion confidencial: solo por canales cifrados (TLS 1.2+, SFTP, correo cifrado)
- Prohibido enviar informacion confidencial por correo sin cifrar
- Uso de DLP para detectar transmision no autorizada de datos sensibles
- Acuerdos de confidencialidad (NDA) con todos los terceros

### 6.2 Redes

- Segmentacion: red corporativa separada de red de invitados y red de produccion
- Firewall perimetral con reglas de deny-all por defecto
- VPN obligatoria para acceso remoto (WireGuard, certificados de cliente)
- Wi-Fi corporativo: WPA3 Enterprise con autenticacion RADIUS

---

## 7. Relacion con Proveedores (A.5.19, A.5.20, A.5.21, A.5.22)

### 7.1 Evaluacion de Proveedores

Todos los proveedores con acceso a informacion deben:
1. Completar cuestionario de seguridad antes de contratacion
2. Demostrar certificacion ISO 27001 o controles equivalentes
3. Aceptar clausulas de seguridad y auditabilidad en contrato
4. Someterse a evaluacion anual de desempeno en seguridad

### 7.2 Proveedores Criticos Actuales

| Proveedor | Servicio | Clasificacion | Ultima Evaluacion | Resultado |
|-----------|----------|---------------|-------------------|-----------|
| AWS | Infraestructura cloud | Critico | 2025-01-15 | Satisfactorio |
| GitHub | Repositorios de codigo | Critico | 2025-02-01 | Satisfactorio |
| Slack | Comunicacion interna | Alto | 2024-11-20 | Satisfactorio |
| DataGuard MX | Destruccion de documentos | Medio | 2024-09-10 | Con observaciones |
| CloudFlare | CDN y proteccion DDoS | Alto | 2025-03-01 | Satisfactorio |

### 7.3 Clausulas Contractuales Obligatorias

- Notificacion de brechas de seguridad en 24 horas
- Derecho de auditoria con previo aviso de 15 dias
- Destruccion o devolucion de datos al terminar contrato
- Subcontratacion solo con aprobacion previa por escrito
- Cumplimiento con legislacion de proteccion de datos aplicable

**Hallazgo pendiente:** El proveedor DataGuard MX no presento evidencia de destruccion certificada para 2 lotes de documentos del Q3 2024.

---

## 8. Gestion de Incidentes (A.5.24, A.5.25, A.5.26, A.5.27)

### 8.1 Clasificacion de Incidentes

| Severidad | Descripcion | Tiempo de Respuesta | Escalacion |
|-----------|-------------|--------------------|-----------| 
| P1 - Critica | Brecha de datos, ransomware, indisponibilidad total | 15 minutos | CISO + Direccion General |
| P2 - Alta | Compromiso de cuenta privilegiada, ataque activo | 1 hora | CISO + Gerente de TI |
| P3 - Media | Malware contenido, phishing exitoso sin exfiltracion | 4 horas | Lider Tecnico Seguridad |
| P4 - Baja | Intento de phishing reportado, alerta informativa | 24 horas | Equipo de Seguridad |

### 8.2 Proceso de Respuesta

1. Deteccion y reporte (cualquier empleado via canal #seguridad o correo incidentes@acme-corp.com)
2. Triaje y clasificacion (Equipo de Seguridad, <30 min)
3. Contencion inmediata (aislar sistemas afectados)
4. Erradicacion (eliminar causa raiz)
5. Recuperacion (restaurar operacion normal)
6. Lecciones aprendidas (post-mortem dentro de 5 dias habiles)

### 8.3 Incidentes Registrados (Ultimos 12 Meses)

| Fecha | Tipo | Severidad | Estado | Tiempo Resolucion |
|-------|------|-----------|--------|-------------------|
| 2025-04-12 | Phishing dirigido a CFO | P2 | Cerrado | 3 horas |
| 2025-03-28 | Credenciales expuestas en repositorio publico | P2 | Cerrado | 45 minutos |
| 2025-02-15 | Ransomware en estacion de trabajo (contenido) | P1 | Cerrado | 6 horas |
| 2025-01-20 | Acceso no autorizado a cuenta de pruebas | P3 | Cerrado | 2 dias |
| 2024-12-05 | DDoS a portal de clientes | P2 | Cerrado | 1.5 horas |
| 2024-11-18 | Fuga de datos por empleado saliente | P1 | Cerrado | 48 horas |
| 2024-09-30 | Vulnerabilidad explotada en dependencia (Log4j legacy) | P2 | Cerrado | 4 horas |

**Hallazgo pendiente:** El incidente de fuga de datos del 18 de noviembre 2024 tardo 48 horas en resolverse, excediendo el SLA de 15 minutos para P1. El post-mortem identifico falta de herramientas DLP efectivas y retraso en la revocacion de accesos del empleado saliente.

---

## 9. Continuidad del Negocio (A.5.29, A.5.30)

### 9.1 Servicios Criticos

| Servicio | RTO | RPO | Estrategia |
|----------|-----|-----|-----------|
| Portal de clientes | 4 horas | 1 hora | Multi-AZ en AWS, failover automatico |
| Correo electronico | 2 horas | 0 (sincronico) | Microsoft 365 con redundancia |
| Repositorios de codigo | 8 horas | 0 (replicacion Git) | GitHub Enterprise con backup S3 |
| ERP (SAP) | 12 horas | 6 horas | Backup diario, restore manual |
| Telefonia VoIP | 4 horas | N/A | Proveedor SaaS con SLA 99.9% |

### 9.2 Plan de Continuidad

- Ejercicio tabletop: semestral (ultimo: enero 2025)
- Prueba tecnica de failover: anual (ultimo: noviembre 2024)
- Plan de comunicacion de crisis documentado y distribuido
- Sitio alterno: capacidad en region us-west-2 de AWS (DR frio)

**Hallazgo pendiente:** No se ha realizado un ejercicio completo de DR que incluya restauracion de ERP. El RTO declarado de 12 horas no ha sido validado con prueba practica.

---

## 10. Cumplimiento Legal y Regulatorio (A.5.31, A.5.34, A.5.36)

### 10.1 Marco Regulatorio Aplicable

- Ley Federal de Proteccion de Datos Personales en Posesion de Particulares (LFPDPPP)
- Ley General de Proteccion de Datos Personales en Posesion de Sujetos Obligados
- NOM-151-SCFI-2002 (Conservacion de mensajes de datos)
- Requisitos contractuales de clientes (SOC 2 Type II para 3 clientes)

### 10.2 Proteccion de Datos Personales

- Aviso de privacidad publicado y actualizado
- Registro de bases de datos personales ante INAI
- Proceso documentado para derechos ARCO (Acceso, Rectificacion, Cancelacion, Oposicion)
- Oficial de Proteccion de Datos designado: Lic. Carlos Ruiz
- Evaluacion de impacto en privacidad para nuevos proyectos

### 10.3 Auditorias

- Auditoria interna SGSI: semestral
- Auditoria de certificacion ISO 27001: anual (proxima: septiembre 2025)
- Auditoria SOC 2 Type II: anual (proxima: agosto 2025)
- Revision por la Direccion: trimestral

---

## Historial de Cambios

| Version | Fecha | Cambios | Aprobado por |
|---------|-------|---------|--------------|
| 1.0 | 2023-01-10 | Creacion inicial | Comite de Seguridad |
| 1.5 | 2023-09-01 | Adicion de politica de proveedores y BCP | Comite de Seguridad |
| 2.0 | 2024-03-15 | Actualizacion completa a ISO 27001:2022 | Comite de Seguridad |
| 2.1 | 2024-09-20 | Actualizacion de SLAs y roles | Comite de Seguridad |

---

*Documento clasificado como: INTERNO*
*Prohibida su reproduccion o distribucion sin autorizacion del Comite de Seguridad de la Informacion.*
