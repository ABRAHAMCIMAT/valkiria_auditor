# Valkiria Auditor — Épicas e Historias de Usuario (INVEST)

**Versión:** 1.0
**Fecha:** 2026-10-20
**Proyecto:** Sistema multi-agente de auditoría ISO/IEC 27001 (Proyecto Integrador MNA — Equipo 16)
**Estándares cubiertos:** ISO/IEC 27001:2013, ISO/IEC 27001:2022, ISO 19011:2018 (metodología de auditoría), ISO 27005 (gestión de riesgos)

---

## Resumen del proyecto

Valkiria Auditor es un sistema multi-agente que automatiza auditorías de cumplimiento ISO/IEC 27001. Combina un pipeline RAG sobre Amazon Bedrock Knowledge Bases (ingesta, chunking semántico, embeddings y almacenamiento vectorial), un sistema de agentes especializados (planificación, evidencia, controles organizacionales A.5, personas A.6, físicos A.7, tecnológicos A.8 y consolidación), cuatro frameworks de orquestación intercambiables (Strands Agents, LangGraph, CrewAI y comp2013 para ISO 27001:2013), un pipeline SAST para evaluar código fuente, un frontend SPA multi-tenant con autenticación Cognito y una capa completa de observabilidad.

## Metodología

Las historias se redactaron a partir del código y la documentación del repositorio, se revisaron y mejoraron aplicando el criterio **INVEST** (Independent, Negotiable, Valuable, Estimable, Small, Testable). Cada historia incluye reglas de negocio (RN) derivadas del comportamiento real del sistema y criterios de aceptación en formato **Dado / Cuando / Entonces**. La revisión INVEST de cada historia se documenta en una línea al final de la misma.

---

# ÉPICA-01: Autenticación y gestión de acceso (SaaS multi-tenant)

**Objetivo:** Permitir que auditores de distintas organizaciones accedan a la plataforma de forma segura, con aislamiento de datos por tenant y control de acceso por rol.

## HU-001: Registro de usuario en la plataforma

**Como** auditor externo, **quiero** registrarme en la plataforma con mi usuario y contraseña, **para** poder acceder al sistema de auditoría.

**Reglas de negocio:**
- RN-01: El registro se realiza contra el User Pool de Amazon Cognito (flujo `USER_PASSWORD_AUTH`).
- RN-02: El usuario debe proporcionar un nombre de usuario y una contraseña válidos según la política del User Pool.
- RN-03: Al registrarse, el usuario se asocia a un tenant (grupo Cognito) que determina el alcance de los datos que puede ver.
- RN-04: El registro no otorga acceso a datos de otros tenants.

**Criterios de aceptación:**
- Dado que soy un usuario nuevo, cuando completo el formulario de registro con credenciales válidas, entonces el sistema crea mi cuenta en Cognito y me permite iniciar sesión.
- Dado que intento registrarme con credenciales inválidas o duplicadas, cuando envío el formulario, entonces el sistema muestra un error claro y no crea la cuenta.
- Dado que soy un usuario registrado, cuando el sistema crea mi cuenta, entonces quedo asociado a mi tenant y no tengo acceso a datos de otros tenants.

**Revisión INVEST:** Historia independiente (no depende de otras para su valor), negociable en los campos del formulario, valiosa (habilita el acceso), estimable (1-2 días), pequeña y testeable (flujo de registro verificable contra Cognito).

## HU-002: Inicio de sesión seguro con renovación de sesión

**Como** auditor, **quiero** iniciar sesión de forma segura y mantener mi sesión activa, **para** trabajar sin interrupciones y sin exponer mis credenciales.

**Reglas de negocio:**
- RN-05: La autenticación usa el flujo `USER_PASSWORD_AUTH` de Cognito; nunca se almacenan contraseñas en el cliente.
- RN-06: Los tokens (ID, acceso y refresh) se conservan únicamente en memoria, nunca en `localStorage`, para mitigar ataques XSS.
- RN-07: El token de acceso se renueva automáticamente antes de su expiración mediante el token de refresh.
- RN-08: Toda petición a la API incluye el token de ID en el encabezado `Authorization`.
- RN-09: Si el token expira o es inválido, la API responde `401` y el frontend redirige al usuario a la pantalla de inicio de sesión.

**Criterios de aceptación:**
- Dado que tengo credenciales válidas, cuando inicio sesión, entonces el sistema me autentica, guarda los tokens en memoria y me redirige a la vista principal.
- Dado que mi sesión está activa, cuando el token de acceso está por expirar, entonces el sistema lo renueva automáticamente sin pedirme volver a autenticarme.
- Dado que mi token expiró, cuando hago una petición a la API, entonces recibo `401`, se cierra mi sesión y se me redirige a `/login`.
- Dado que cierro sesión, cuando el sistema limpia los tokens, entonces ya no puedo acceder a rutas protegidas.

**Revisión INVEST:** Independiente, negociable (duración de sesión), valiosa (seguridad y continuidad), estimable, pequeña y testeable (verificación de renovación y expiración de tokens).

## HU-003: Aislamiento multi-tenant y control de acceso por rol

**Como** administrador de la plataforma, **quiero** que cada organización (tenant) vea únicamente sus auditorías y evaluaciones, **para** garantizar la confidencialidad entre clientes.

**Reglas de negocio:**
- RN-10: El tenant se identifica mediante el grupo Cognito (`cognito:groups`) incluido en el token.
- RN-11: El rol del usuario se identifica mediante el atributo personalizado `custom:role` del token.
- RN-12: Las peticiones a la API incluyen el contexto de tenant; el backend filtra los datos por tenant antes de responder.
- RN-13: Un usuario de un tenant no puede leer, modificar ni eliminar datos de otro tenant.

**Criterios de aceptación:**
- Dado que pertenezco al tenant A, cuando consulto la lista de auditorías, entonces solo veo las auditorías del tenant A.
- Dado que intento acceder a un recurso de otro tenant, cuando hago una petición con mi token, entonces el sistema rechaza la petición o devuelve datos vacíos.
- Dado que tengo un rol sin permisos de administración, cuando intento una operación administrativa, entonces el sistema la deniega.

**Revisión INVEST:** Independiente, negociable (definición de roles), valiosa (confidencialidad entre clientes), estimable, pequeña y testeable (pruebas de aislamiento entre tenants).

## HU-004: Protección de rutas y navegación de la SPA

**Como** usuario de la plataforma, **quiero** que las rutas protegidas exijan autenticación y que la navegación sea fluida, **para** no acceder a información sin sesión válida.

**Reglas de negocio:**
- RN-14: Las rutas `/`, `/auditorias`, `/auditorias/:id` y `/evaluaciones` son protegidas; sin sesión redirigen a `/login`.
- RN-15: Las rutas `/login` y `/register` son públicas; con sesión activa redirigen a la vista principal.
- RN-16: La ruta `/acerca` es pública.
- RN-17: La barra de navegación y el pie de página se ocultan en las vistas de login y registro.

**Criterios de aceptación:**
- Dado que no tengo sesión, cuando navego a `/auditorias`, entonces el sistema me redirige a `/login`.
- Dado que tengo sesión activa, cuando navego a `/login`, entonces el sistema me redirige a la vista principal.
- Dado que estoy en la vista de login, cuando se renderiza la página, entonces la barra de navegación y el pie de página no se muestran.

**Revisión INVEST:** Independiente, negociable (qué rutas son públicas), valiosa (seguridad de navegación), estimable, pequeña y testeable (recorridos de rutas).

---

# ÉPICA-02: Gestión de auditorías

**Objetivo:** Permitir al auditor crear, consultar, filtrar y eliminar proyectos de auditoría ISO 27001, cargando los datos de evaluación necesarios.

## HU-005: Crear una auditoría

**Como** auditor, **quiero** crear una auditoría indicando nombre, versión ISO y framework de orquestación, **para** iniciar un proyecto de evaluación de cumplimiento.

**Reglas de negocio:**
- RN-18: El nombre de la auditoría es obligatorio.
- RN-19: La versión ISO es obligatoria: `2022` (93 controles, 4 dominios) o `2013` (114 controles, 14 dominios).
- RN-20: El framework de orquestación solo aplica a ISO 27001:2022 y puede ser `strands`, `langgraph` o `crewai`; para ISO 27001:2013 se usa el orquestador `comp2013` de forma automática.
- RN-21: Al crearse, la auditoría queda en estado `pendiente` con fecha de creación y actualización registradas.
- RN-22: La auditoría se asocia al tenant del usuario que la crea.

**Criterios de aceptación:**
- Dado que soy un auditor autenticado, cuando creo una auditoría con nombre, versión ISO y framework válidos, entonces el sistema la registra en estado `pendiente` y aparece en la lista.
- Dado que intento crear una auditoría sin nombre o sin versión ISO, cuando envío el formulario, entonces el sistema muestra un error de validación y no la crea.
- Dado que selecciono ISO 27001:2013, cuando el formulario se muestra, entonces el selector de framework no aparece (se usa `comp2013` automáticamente).
- Dado que selecciono ISO 27001:2022, cuando el formulario se muestra, entonces puedo elegir entre Strands Agents, LangGraph y CrewAI.

**Revisión INVEST:** Independiente, negociable (campos adicionales), valiosa (inicia el flujo de auditoría), estimable, pequeña y testeable (validaciones y persistencia).

## HU-006: Listar y filtrar auditorías

**Como** auditor, **quiero** ver la lista de mis auditorías y filtrarlas por versión ISO, **para** localizar rápidamente los proyectos en curso.

**Reglas de negocio:**
- RN-23: La lista muestra: nombre, versión ISO, estado de datos cargados, fecha de creación, fecha de completado y acciones.
- RN-24: El filtro por versión ISO admite `todas`, `2022` y `2013`.
- RN-25: La lista solo muestra auditorías del tenant del usuario autenticado.
- RN-26: Mientras la lista se carga, se muestra un indicador de carga.

**Criterios de aceptación:**
- Dado que tengo auditorías creadas, cuando entro a la sección Auditorías, entonces veo la tabla con todas mis auditorías y sus datos.
- Dado que selecciono el filtro `ISO 27001:2022`, cuando aplico el filtro, entonces solo se muestran las auditorías con versión 2022.
- Dado que la lista está cargando, cuando la página se renderiza, entonces se muestra el spinner de carga hasta que llegan los datos.

**Revisión INVEST:** Independiente, negociable (columnas y filtros), valiosa (visibilidad del estado), estimable, pequeña y testeable.

## HU-007: Consultar el detalle de una auditoría

**Como** auditor, **quiero** ver el detalle de una auditoría con sus hallazgos, agentes participantes y resumen de conformidad, **para** analizar los resultados de la evaluación.

**Reglas de negocio:**
- RN-27: El detalle muestra información general (nombre, versión ISO, framework, estado, fechas).
- RN-28: Los hallazgos incluyen: control ISO, descripción, severidad (`alta`, `media`, `baja`) y estado (`abierto`, `en_remediacion`, `cerrado`).
- RN-29: La sección de agentes muestra cada agente de dominio con su estado y número de controles evaluados (A.5: 37, A.6: 8, A.7: 14, A.8: 34).
- RN-30: El resumen muestra total de controles, conformes, no conformes y parcialmente conformes, y el porcentaje de conformidad calculado.
- RN-31: Si la auditoría no existe o no pertenece al tenant, se muestra un estado de error.

**Criterios de aceptación:**
- Dado que tengo una auditoría completada, cuando abro su detalle, entonces veo la información general, los hallazgos con severidad y estado, los agentes con controles evaluados y el resumen de conformidad.
- Dado que el porcentaje de conformidad se calcula, cuando hay `conformes` y `total_controles`, entonces el sistema muestra `round(conformes / total_controles * 100)`.
- Dado que la auditoría no se puede cargar, cuando abro el detalle, entonces se muestra el mensaje de error sin romper la aplicación.

**Revisión INVEST:** Independiente, negociable (qué métricas mostrar), valiosa (análisis de resultados), estimable, pequeña y testeable.

## HU-008: Eliminar una auditoría

**Como** auditor, **quiero** eliminar una auditoría que ya no necesito, **para** mantener mi lista de proyectos ordenada.

**Reglas de negocio:**
- RN-32: Solo se puede eliminar una auditoría del propio tenant.
- RN-33: La eliminación es una acción destructiva; el frontend solicita confirmación antes de ejecutarla.
- RN-34: Al eliminar, la auditoría desaparece de la lista.

**Criterios de aceptación:**
- Dado que tengo una auditoría, cuando confirmo su eliminación, entonces el sistema la elimina y ya no aparece en la lista.
- Dado que intento eliminar una auditoría de otro tenant, cuando ejecuto la acción, entonces el sistema la rechaza.

**Revisión INVEST:** Independiente, negociable (confirmación), valiosa (higiene de datos), estimable, pequeña y testeable.

## HU-009: Cargar datos de evaluación en una auditoría

**Como** auditor, **quiero** cargar los resultados de análisis de seguridad (reportes SAST/DAST, políticas, evidencias) en la auditoría, **para** que el sistema los use en la evaluación automatizada.

**Reglas de negocio:**
- RN-35: Formatos aceptados por archivo individual: Markdown (`.md`), JSON, XML, HTML y CSV.
- RN-36: También se acepta un archivo `.zip` con todos los recursos de evaluación.
- RN-37: La carga se realiza mediante dos pestañas: archivos individuales o paquete `.zip`.
- RN-38: Los archivos cargados se asocian a la auditoría y quedan disponibles para el pipeline de evaluación.

**Criterios de aceptación:**
- Dado que estoy creando una auditoría, cuando selecciono archivos individuales en formato `.md`, `.json`, `.xml`, `.html` o `.csv`, entonces el sistema los acepta y los asocia a la auditoría.
- Dado que tengo un paquete de recursos, cuando selecciono la pestaña `.zip` y subo el archivo, entonces el sistema lo acepta como datos de evaluación.
- Dado que intento subir un formato no soportado, cuando selecciono el archivo, entonces el sistema lo rechaza con un mensaje de error.

**Revisión INVEST:** Independiente, negociable (formatos admitidos), valiosa (alimenta la evaluación), estimable, pequeña y testeable.

---

# ÉPICA-03: Pipeline SAST de evaluación de código

**Objetivo:** Evaluar automáticamente el código fuente de una aplicación contra controles ISO 27001 mediante análisis estático (SAST) y un agente de evaluación.

## HU-010: Subir código fuente mediante URL presigned

**Como** auditor, **quiero** subir un `.zip` con el código fuente de la aplicación a evaluar, **para** iniciar el análisis de seguridad.

**Reglas de negocio:**
- RN-39: El frontend solicita una URL presigned de tipo `PUT` al endpoint de la Lambda `iso27001-sast-upload-url`.
- RN-40: La URL expira en 3600 segundos por defecto (configurable).
- RN-41: El archivo debe ser `.zip` con `ContentType: application/zip`.
- RN-42: La subida incluye metadatos: usuario que sube y nombre del proyecto.
- RN-43: El `.zip` se almacena en el bucket S3 de origen (`uploads/app.zip`), lo que dispara el pipeline automáticamente.

**Criterios de aceptación:**
- Dado que estoy en la sección de evaluación, cuando solicito subir un `.zip`, entonces el sistema genera una URL presigned de `PUT` válida por 1 hora.
- Dado que subo el `.zip` con la URL presigned, cuando el archivo llega a S3, entonces se registra con los metadatos de usuario y proyecto.
- Dado que la URL expiró, cuando intento subir el archivo, entonces S3 rechaza la operación y el frontend solicita una nueva URL.

**Revisión INVEST:** Independiente, negociable (tiempo de expiración), valiosa (habilita el análisis), estimable, pequeña y testeable.

## HU-011: Ejecutar el análisis SAST al subir el código

**Como** auditor, **quiero** que el sistema ejecute automáticamente un análisis estático de seguridad sobre el código subido, **para** detectar vulnerabilidades sin intervención manual.

**Reglas de negocio:**
- RN-44: El evento `PutObject` en el bucket de origen dispara AWS CodePipeline (`iso27001-sast-pipeline`).
- RN-45: El pipeline tiene tres etapas: Source (S3 `.zip`), SAST (CodeBuild) y Agent Evaluation (Lambda).
- RN-46: La etapa SAST descomprime el `.zip` y ejecuta Semgrep con reglas OWASP y auditoría de seguridad.
- RN-47: Los hallazgos crudos se almacenan en `sast-reports/` del bucket de resultados.
- RN-48: El pipeline continúa a la etapa de evaluación solo si la etapa SAST completa con éxito.

**Criterios de aceptación:**
- Dado que se sube un `.zip` al bucket de origen, cuando S3 genera el evento, entonces CodePipeline inicia la ejecución automáticamente.
- Dado que el pipeline está en la etapa SAST, cuando CodeBuild descomprime y ejecuta Semgrep, entonces los hallazgos se guardan en `sast-reports/`.
- Dado que la etapa SAST falla, cuando el pipeline evalúa el resultado, entonces la ejecución se detiene y no continúa a la evaluación.

**Revisión INVEST:** Independiente, negociable (reglas de escaneo), valiosa (detección temprana de vulnerabilidades), estimable, pequeña y testeable (ejecución de pipeline).

## HU-012: Evaluar hallazgos SAST con agente y mapeo a ISO 27001

**Como** auditor, **quiero** que un agente especializado evalúe los hallazgos SAST y los mapee a controles ISO 27001, **para** obtener hallazgos de auditoría accionables.

**Reglas de negocio:**
- RN-49: La Lambda `iso27001-sast-agent-evaluation` se invoca como acción de CodePipeline tras la etapa SAST.
- RN-50: La Lambda recupera los resultados SAST más recientes de `sast-reports/`.
- RN-51: Los hallazgos se envían a un agente Bedrock respaldado por la base de conocimiento ISO 27001, que mapea cada vulnerabilidad a controles.
- RN-52: El reporte de evaluación se almacena en `agent-evaluations/` del bucket de resultados.
- RN-53: La Lambda reporta éxito o fallo de vuelta a CodePipeline.

**Criterios de aceptación:**
- Dado que existen resultados SAST en `sast-reports/`, cuando la Lambda de evaluación se ejecuta, entonces recupera los hallazgos y los envía al agente Bedrock.
- Dado que el agente procesa los hallazgos, cuando genera el reporte, entonces cada vulnerabilidad queda mapeada a controles ISO 27001 y el reporte se guarda en `agent-evaluations/`.
- Dado que la evaluación falla, cuando la Lambda termina, entonces reporta el fallo a CodePipeline y la ejecución se marca como fallida.

**Revisión INVEST:** Independiente, negociable (modelo y reglas de mapeo), valiosa (convierte hallazgos técnicos en hallazgos de auditoría), estimable, pequeña y testeable.

---

# ÉPICA-04: Sistema multi-agente de auditoría ISO 27001:2022

**Objetivo:** Ejecutar auditorías completas mediante agentes especializados coordinados por un orquestador, siguiendo la metodología ISO 19011.

## HU-013: Generar el plan de auditoría (agente de planificación)

**Como** auditor, **quiero** que el agente de planificación genere un plan de auditoría con alcance, objetivos, criterios, cronograma y equipo, **para** preparar la auditoría conforme a ISO 19011.

**Reglas de negocio:**
- RN-54: El agente de planificación recibe el contexto de la organización y el tipo de auditoría (`internal`, `certification`, `surveillance`).
- RN-55: El plan incluye: alcance, objetivos, criterios, cronograma, roles del equipo y controles en alcance.
- RN-56: El cronograma se estima según el tamaño de la organización: pequeña (<50), mediana (50-500) o grande (>500).
- RN-57: El agente consulta el catálogo de controles ISO 27001:2022 (A.5: 37, A.6: 8, A.7: 14, A.8: 34; total 93).
- RN-58: El plan se genera en formato JSON estructurado.

**Criterios de aceptación:**
- Dado que proporciono el contexto de una organización mediana, cuando el agente de planificación se ejecuta, entonces genera un plan con las 4 fases (planificación, recopilación de evidencia, evaluación por dominio, consolidación) y duraciones estimadas.
- Dado que solicito el catálogo de controles, cuando consulto el dominio `A.5`, entonces el agente devuelve 37 controles con su rango y descripción.
- Dado que el tipo de auditoría es `certification`, cuando se genera el plan, entonces el tipo queda registrado en la salida.

**Revisión INVEST:** Independiente, negociable (heurísticas de duración), valiosa (estructura la auditoría), estimable, pequeña y testeable.

## HU-014: Recopilar evidencia documental (agente de evidencia)

**Como** auditor, **quiero** que el agente de evidencia recupere y organice la evidencia documental de los controles en alcance, **para** evaluar el cumplimiento con base en evidencia real.

**Reglas de negocio:**
- RN-59: El agente consulta la base de conocimiento mediante `retrieve_and_generate` con búsqueda semántica (5 resultados por control).
- RN-60: Para cada control devuelve: evidencia encontrada, número de fuentes, URIs de S3 y extractos.
- RN-61: La suficiencia de evidencia se evalúa por tipos requeridos según el dominio (A.5: política, procedimiento, registros de revisión, evidencia de implementación; A.6: registros de RH, capacitación, acuerdos; A.7: plan de seguridad física, logs de acceso, mantenimiento; A.8: configuración técnica, escaneos, arquitectura).
- RN-62: La evidencia se considera suficiente si el puntaje de suficiencia es ≥ 0.75.
- RN-63: Si la base de conocimiento no está configurada (`KNOWLEDGE_BASE_ID` vacío), el agente devuelve un error controlado.

**Criterios de aceptación:**
- Dado que solicito evidencia para el control `A.5.1`, cuando el agente consulta la base de conocimiento, entonces devuelve las fuentes con URI y extracto, o indica que no encontró evidencia.
- Dado que la evidencia cubre los tipos requeridos, cuando se evalúa la suficiencia, entonces el puntaje es ≥ 0.75 y la evidencia se marca como suficiente.
- Dado que faltan tipos de evidencia, cuando se evalúa la suficiencia, entonces el agente lista los tipos faltantes y recomienda evidencia adicional.

**Revisión INVEST:** Independiente, negociable (umbral de suficiencia), valiosa (base objetiva de la evaluación), estimable, pequeña y testeable.

## HU-015: Evaluar controles organizacionales A.5

**Como** auditor, **quiero** que el agente de controles organizacionales evalúe los 37 controles A.5, **para** determinar la conformidad de políticas, roles, gestión de proveedores y respuesta a incidentes.

**Reglas de negocio:**
- RN-64: El agente evalúa los controles A.5.1–A.5.37 con base en la evidencia recopilada.
- RN-65: Para cada control emite: nivel de conformidad, puntaje de madurez (escala CMM 0-5), brechas y hallazgos.
- RN-66: La evaluación usa temperatura 0.0 para asegurar consistencia.
- RN-67: El alcance puede limitarse a un subconjunto de controles.

**Criterios de aceptación:**
- Dado que existe evidencia para los controles A.5, cuando el agente se ejecuta, entonces devuelve una evaluación por control con conformidad, madurez, brechas y hallazgos.
- Dado que limito el alcance a controles específicos, cuando ejecuto la evaluación, entonces solo se evalúan los controles solicitados.

**Revisión INVEST:** Independiente, negociable (subconjuntos), valiosa (núcleo de la auditoría), estimable, pequeña y testeable.

## HU-016: Evaluar controles de personas A.6

**Como** auditor, **quiero** que el agente de controles de personas evalúe los 8 controles A.6, **para** verificar screening, capacitación, términos de empleo, trabajo remoto y reporte de eventos.

**Reglas de negocio:**
- RN-68: El agente evalúa los controles A.6.1–A.6.8 con base en la evidencia.
- RN-69: Evalúa específicamente: verificación de antecedentes, efectividad de la capacitación, controles de trabajo remoto y reporte de eventos de seguridad.
- RN-70: Emite conformidad, madurez, brechas y hallazgos por control.

**Criterios de aceptación:**
- Dado que existe evidencia de personas (screening, capacitación, offboarding), cuando el agente se ejecuta, entonces devuelve la evaluación de los 8 controles A.6 con sus hallazgos.
- Dado que la evidencia de capacitación es insuficiente, cuando se evalúa A.6.3, entonces el hallazgo refleja la brecha de evidencia.

**Revisión INVEST:** Independiente, negociable, valiosa (cubre el factor humano), estimable, pequeña y testeable.

## HU-017: Evaluar controles físicos A.7

**Como** auditor, **quiero** que el agente de controles físicos evalúe los 14 controles A.7, **para** verificar perímetros de seguridad, control de acceso físico, protección ambiental y seguridad de equipos.

**Reglas de negocio:**
- RN-71: El agente evalúa los controles A.7.1–A.7.14 con base en la evidencia.
- RN-72: Evalúa: perímetros de seguridad física, controles de entrada, protección contra amenazas ambientales, seguridad de equipos, políticas de escritorio/pantalla limpia y disposición segura de equipos.
- RN-73: Emite conformidad, madurez, brechas y hallazgos por control.

**Criterios de aceptación:**
- Dado que existe evidencia de seguridad física (CCTV, perímetros, mantenimiento), cuando el agente se ejecuta, entonces devuelve la evaluación de los 14 controles A.7.
- Dado que una ubicación no tiene control de acceso documentado, cuando se evalúa A.7.2, entonces el hallazgo lo señala como brecha.

**Revisión INVEST:** Independiente, negociable, valiosa (cubre seguridad física), estimable, pequeña y testeable.

## HU-018: Evaluar controles tecnológicos A.8

**Como** auditor, **quiero** que el agente de controles tecnológicos evalúe los 34 controles A.8, **para** verificar control de acceso, criptografía, seguridad de red, gestión de vulnerabilidades y desarrollo seguro.

**Reglas de negocio:**
- RN-74: El agente evalúa los controles A.8.1–A.8.34 con base en la evidencia.
- RN-75: Evalúa: control de acceso, gestión de vulnerabilidades, desarrollo seguro, seguridad de red y operaciones.
- RN-76: Puede incorporar resultados SAST como evidencia técnica adicional.
- RN-77: Emite conformidad, madurez, brechas y hallazgos por control.

**Criterios de aceptación:**
- Dado que existe evidencia técnica (reportes SAST/DAST, configuraciones), cuando el agente se ejecuta, entonces devuelve la evaluación de los 34 controles A.8.
- Dado que un reporte SAST contiene vulnerabilidades críticas, cuando se evalúa el control de gestión de vulnerabilidades, entonces el hallazgo refleja la no conformidad.

**Revisión INVEST:** Independiente, negociable, valiosa (cubre el dominio tecnológico), estimable, pequeña y testeable.

## HU-019: Consolidar hallazgos y generar el reporte final (orquestador)

**Como** auditor, **quiero** que el orquestador consolide los hallazgos de todos los agentes, verifique su consistencia y genere el reporte final con resumen ejecutivo, **para** obtener una conclusión de auditoría confiable.

**Reglas de negocio:**
- RN-78: El orquestador invoca a los sub-agentes en secuencia: planificación → evidencia → evaluación por dominio → consolidación.
- RN-79: La verificación de consistencia detecta: desalineación conformidad/madurez (conforme con madurez < 3, o no conformidad mayor con madurez > 2) y contradicciones entre evaluaciones del mismo control.
- RN-80: El resumen ejecutivo calcula: tasa de conformidad, veredicto (recomendación de certificación) y nivel de madurez global (Initial, Repeatable, Defined, Managed, Optimized).
- RN-81: El veredicto se determina por reglas: >5 no conformidades mayores → no recomendado; >0 mayores → condicional (90 días); >10 menores → recomendado con condiciones; en otro caso → recomendado.
- RN-82: El reporte final incluye: resumen ejecutivo, hallazgos por dominio, recomendaciones priorizadas y puntaje de madurez global.
- RN-83: Los hallazgos se persisten (DynamoDB/S3) y el reporte se guarda en S3.

**Criterios de aceptación:**
- Dado que todos los agentes de dominio completaron su evaluación, cuando el orquestador consolida, entonces genera un reporte con resumen ejecutivo, hallazgos por dominio, recomendaciones y madurez global.
- Dado que un control aparece como conforme con madurez 2, cuando se verifica la consistencia, entonces se registra una desalineación `alignment_mismatch`.
- Dado que hay 3 no conformidades mayores, cuando se genera el resumen ejecutivo, entonces el veredicto es `CONDITIONAL CERTIFICATION`.
- Dado que el reporte se genera, cuando se persiste, entonces queda almacenado en S3 con el `audit_id` correspondiente.

**Revisión INVEST:** Independiente, negociable (reglas de veredicto), valiosa (conclusión accionable), estimable, pequeña y testeable.

---

# ÉPICA-05: Orquestación multi-framework

**Objetivo:** Ejecutar la misma auditoría con distintos frameworks de orquestación de agentes, seleccionables desde el frontend, para comparar y validar resultados.

## HU-020: Ejecutar auditoría con Strands Agents

**Como** auditor, **quiero** ejecutar la auditoría con el framework Strands Agents (patrón "Agents as Tools"), **para** obtener el reporte consolidado con trazabilidad del flujo.

**Reglas de negocio:**
- RN-84: El orquestador Strands envuelve a los sub-agentes como herramientas (`plan_audit`, `collect_evidence`, `evaluate_organizational_controls`, `evaluate_people_controls`, `evaluate_physical_controls`, `evaluate_technological_controls`).
- RN-85: El orquestador invoca todas las herramientas en orden y genera el reporte consolidado.
- RN-86: El reporte se persiste en S3 y se devuelve con métricas de flujo y diagrama Mermaid.
- RN-87: El endpoint es `POST /audit/strands`; requiere `organization_context` (si falta, responde `400`).

**Criterios de aceptación:**
- Dado que envío `organization_context` válido, cuando ejecuto `POST /audit/strands`, entonces el sistema devuelve `200` con `audit_id`, reporte, métricas de flujo y diagrama Mermaid.
- Dado que omito `organization_context`, cuando ejecuto el endpoint, entonces el sistema responde `400` con el error correspondiente.
- Dado que el orquestador ejecuta, cuando invoca las herramientas, entonces las ejecuta en el orden definido (plan → evidencia → dominios → consolidación).

**Revisión INVEST:** Independiente, negociable (modelos por agente), valiosa (framework principal), estimable, pequeña y testeable.

## HU-021: Ejecutar auditoría con LangGraph

**Como** auditor, **quiero** ejecutar la auditoría con LangGraph (grafo de estado con fan-out paralelo), **para** evaluar los dominios en paralelo y reducir el tiempo de auditoría.

**Reglas de negocio:**
- RN-88: El flujo se modela como `StateGraph`: START → planning → evidence → fan-out de evaluadores → consolidation → END.
- RN-89: Los evaluadores de dominio (org, people, phys, tech) se ejecutan en paralelo (fan-out).
- RN-90: El estado tipado (`AuditState`) fluye a través del grafo con aristas condicionales.
- RN-91: El endpoint es `POST /audit/langgraph`; requiere `organization_context`.

**Criterios de aceptación:**
- Dado que envío `organization_context` válido, cuando ejecuto `POST /audit/langgraph`, entonces el sistema devuelve `200` con el reporte consolidado.
- Dado que el grafo se ejecuta, cuando llega al nodo de fan-out, entonces los cuatro evaluadores de dominio se ejecutan en paralelo antes de la consolidación.
- Dado que omito `organization_context`, cuando ejecuto el endpoint, entonces el sistema responde `400`.

**Revisión INVEST:** Independiente, negociable (paralelismo), valiosa (rendimiento), estimable, pequeña y testeable.

## HU-022: Ejecutar auditoría con CrewAI

**Como** auditor, **quiero** ejecutar la auditoría con CrewAI (agentes por rol con tareas encadenadas), **para** obtener el reporte con el patrón de crew.

**Reglas de negocio:**
- RN-92: Los agentes se definen por rol, objetivo y backstory; las tareas tienen `expected_output` y encadenan contexto.
- RN-93: El proceso puede ser secuencial o jerárquico (con delegación del manager).
- RN-94: El flujo: planificación → evidencia → A.5 → A.6 → A.7 → A.8 → consolidación.
- RN-95: El endpoint es `POST /audit/crewai`; requiere `organization_context`.

**Criterios de aceptación:**
- Dado que envío `organization_context` válido, cuando ejecuto `POST /audit/crewai`, entonces el sistema devuelve `200` con el reporte consolidado.
- Dado que el crew se ejecuta en proceso secuencial, cuando las tareas se encadenan, entonces cada tarea recibe el contexto de la anterior.
- Dado que omito `organization_context`, cuando ejecuto el endpoint, entonces el sistema responde `400`.

**Revisión INVEST:** Independiente, negociable (proceso secuencial vs jerárquico), valiosa (alternativa de orquestación), estimable, pequeña y testeable.

## HU-023: Ejecutar auditoría ISO 27001:2013 con juez LLM (comp2013)

**Como** auditor, **quiero** ejecutar una auditoría ISO 27001:2013 con los agentes de gobernanza, organizacional y técnico, y un juez LLM opcional, **para** evaluar organizaciones con la versión 2013 del estándar.

**Reglas de negocio:**
- RN-96: El orquestador `comp2013` evalúa cláusulas 4-10 (gobernanza), Anexo A A.5-A.8/A.15/A.16/A.18 (organizacional) y A.9-A.14/A.17 (técnico).
- RN-97: Para cada control recupera evidencia de S3 Vectors (top-K=3) e invoca al agente especialista con temperatura 0.0.
- RN-98: Los hallazgos se clasifican en: `No conformidad mayor`, `No conformidad menor`, `Conforme`, `No se puede evaluar`, `Oportunidad de Mejora`.
- RN-99: Si `run_judge=true`, un juez LLM puntúa la precisión de cada hallazgo (`precision_score`).
- RN-100: El reporte se persiste en S3 (`metrics/comp2013/{audit_id}/report.json`).
- RN-101: El endpoint es `POST /audit/comp2013`; requiere `organization_context` (si falta, `400`).
- RN-102: La respuesta limita los hallazgos a los primeros 50 para controlar el tamaño.

**Criterios de aceptación:**
- Dado que envío `organization_context` válido, cuando ejecuto `POST /audit/comp2013`, entonces el sistema devuelve `200` con `audit_id`, conteos de severidad, métricas por agente y hallazgos.
- Dado que activo `run_judge=true`, cuando se evalúa cada control, entonces cada hallazgo incluye `judge_score` y `judge_detail`.
- Dado que un agente devuelve JSON no parseable, cuando se procesa la respuesta, entonces el hallazgo se registra con `parse_error: true` sin romper la auditoría.
- Dado que omito `organization_context`, cuando ejecuto el endpoint, entonces el sistema responde `400`.

**Revisión INVEST:** Independiente, negociable (juez opcional), valiosa (soporta la versión 2013), estimable, pequeña y testeable.

---

# ÉPICA-06: RAG y base de conocimiento

**Objetivo:** Construir y operar la base de conocimiento que alimenta a los agentes con el contenido normativo y la evidencia documental.

## HU-024: Ingesta de documentos a la base de conocimiento

**Como** administrador del sistema, **quiero** ingestar documentos normativos y organizacionales en la base de conocimiento, **para** que los agentes tengan el contenido necesario para auditar.

**Reglas de negocio:**
- RN-103: Se ingieren 35+ documentos en 7 categorías: ISO 27001, ejemplos de auditoría, metodología de auditoría, controles CISO Assistant (YAML), no conformidades, documentos del patrocinador y toolkit ISO 27001:2022.
- RN-104: Formatos soportados: PDF, DOCX, XLSX, YAML y MD.
- RN-105: Los documentos se almacenan en S3 con prefijos: `raw/`, `processed/`, `eda_results/`, `validation/`, `fine-tuning/`.
- RN-106: El pipeline de ingesta (EDA → chunking/ingesta KB → validación RAG) se orquesta con Step Functions.

**Criterios de aceptación:**
- Dado que tengo un documento PDF de la norma, cuando se ejecuta la ingesta, entonces el documento se procesa y queda disponible en la base de conocimiento.
- Dado que un documento tiene un formato no soportado, cuando se intenta ingestar, entonces el pipeline lo rechaza o lo marca como error sin detener el resto.
- Dado que la ingesta termina, cuando se valida el pipeline, entonces los documentos quedan en los prefijos S3 correspondientes.

**Revisión INVEST:** Independiente, negociable (categorías), valiosa (base del RAG), estimable, pequeña y testeable.

## HU-025: Chunking semántico y jerárquico de documentos

**Como** administrador del sistema, **quiero** dividir los documentos en fragmentos semánticos óptimos, **para** mejorar la precisión de la recuperación.

**Reglas de negocio:**
- RN-107: El chunking semántico usa: `maxTokens=512`, `bufferSize=1`, `breakpointPercentileThreshold=95`, solapamiento 20%.
- RN-108: Los documentos estructurados (SOA, registro de riesgos) usan chunking jerárquico.
- RN-109: El chunking semántico fue seleccionado por métricas: Recall@5=0.85, MRR=0.71 (vs. fijo 300: 0.72/0.58; fijo 512: 0.78/0.64; jerárquico: 0.82/0.69).

**Criterios de aceptación:**
- Dado que un documento se procesa, cuando se aplica chunking semántico, entonces los fragmentos respetan los parámetros configurados (512 tokens, 20% de solapamiento).
- Dado que el documento es estructurado (SOA o registro de riesgos), cuando se procesa, entonces se aplica chunking jerárquico.
- Dado que se comparan estrategias de chunking, cuando se evalúa la recuperación, entonces el semántico supera a los fijos en Recall@5 y MRR.

**Revisión INVEST:** Independiente, negociable (parámetros), valiosa (calidad de recuperación), estimable, pequeña y testeable.

## HU-026: Generación de embeddings y almacenamiento vectorial

**Como** administrador del sistema, **quiero** generar embeddings de los fragmentos y almacenarlos en un índice vectorial, **para** habilitar la búsqueda semántica.

**Reglas de negocio:**
- RN-110: Los embeddings se generan con Amazon Titan Text Embeddings V2 (1024 dimensiones, normalización L2).
- RN-111: El almacenamiento vectorial usa S3 Vectors (producción) u OpenSearch Serverless (diseño alternativo).
- RN-112: El objetivo de producción es 512 dimensiones (99% de precisión retenida, 50% de ahorro de almacenamiento).
- RN-113: La latencia objetivo de recuperación es ~68 ms.

**Criterios de aceptación:**
- Dado que los fragmentos están listos, cuando se genera el embedding, entonces cada fragmento queda representado con 1024 dimensiones normalizadas.
- Dado que el índice vectorial está poblado, cuando se consulta con un vector, entonces se devuelven los vecinos más cercanos por distancia coseno.

**Revisión INVEST:** Independiente, negociable (dimensionalidad), valiosa (búsqueda semántica), estimable, pequeña y testeable.

## HU-027: Recuperación con filtrado por metadatos y citas

**Como** auditor, **quiero** que la recuperación filtre por metadatos relevantes y devuelva citas de las fuentes, **para** que los hallazgos sean trazables a documentos reales.

**Reglas de negocio:**
- RN-114: Los metadatos de filtrado son: `document_type`, `source_category`, `compliance_domain`, `iso_control_reference`, `temporal_relevance`.
- RN-115: Los metadatos fueron validados estadísticamente (Chi-cuadrado y ANOVA, p<0.001).
- RN-116: La recuperación devuelve citas con URI de S3 y extractos del texto fuente.
- RN-117: La búsqueda usa `overrideSearchType: SEMANTIC` con 5 resultados por defecto (configurable).

**Criterios de aceptación:**
- Dado que consulto por un control específico, cuando el agente recupera evidencia, entonces los resultados incluyen la URI de la fuente y el extracto citado.
- Dado que aplico un filtro por `compliance_domain`, cuando se ejecuta la búsqueda, entonces solo se devuelven fragmentos del dominio solicitado.
- Dado que la base de conocimiento no está configurada, cuando se consulta, entonces el sistema devuelve un error controlado sin fallar.

**Revisión INVEST:** Independiente, negociable (metadatos), valiosa (trazabilidad), estimable, pequeña y testeable.

---

# ÉPICA-07: Observabilidad y métricas

**Objetivo:** Garantizar la trazabilidad, el monitoreo y la mejora continua del sistema multi-agente.

## HU-028: Trazabilidad del flujo de orquestación

**Como** administrador del sistema, **quiero** registrar la ejecución de cada nodo del flujo de orquestación (agente, modelo, tiempos, tokens, costo), **para** diagnosticar cuellos de botella y auditar el comportamiento del sistema.

**Reglas de negocio:**
- RN-118: El `FlowTracker` registra por nodo: tiempos, espera, dependencias, tokens de entrada/salida, llamadas a herramientas, errores, costo y turnos.
- RN-119: Cada ejecución se identifica por `audit_id`, `session_id` y `actor_id`.
- RN-120: El tracker detecta cuellos de botella con causa raíz.
- RN-121: Las métricas se publican a CloudWatch y se persisten en S3.

**Criterios de aceptación:**
- Dado que se ejecuta una auditoría, cuando el orquestador recorre los nodos, entonces cada nodo queda registrado con sus métricas (tiempo, tokens, herramientas).
- Dado que un nodo tarda más que el umbral, cuando se finaliza el flujo, entonces el tracker identifica el cuello de botella y su causa.

**Revisión INVEST:** Independiente, negociable (qué métricas), valiosa (diagnóstico), estimable, pequeña y testeable.

## HU-029: Métricas por agente y publicación a CloudWatch

**Como** administrador del sistema, **quiero** consultar métricas por agente (controles evaluados, latencia, tokens) y publicarlas a CloudWatch, **para** monitorear el rendimiento y el costo.

**Reglas de negocio:**
- RN-122: Por agente se reportan: controles evaluados, latencia total y promedio, tokens de entrada y salida.
- RN-123: El `ObservabilityCollector` integra las métricas de nivel 3 (por nodo) con publicación a CloudWatch.
- RN-124: Las alertas se configuran sobre las métricas publicadas.
- RN-125: El reporte de auditoría incluye `agent_metrics` y `flow_metrics`.

**Criterios de aceptación:**
- Dado que una auditoría termina, cuando se genera el reporte, entonces incluye las métricas por agente (controles, latencia, tokens).
- Dado que las métricas se publican, cuando se consulta CloudWatch, entonces aparecen las series por agente y nodo.

**Revisión INVEST:** Independiente, negociable (umbrales de alerta), valiosa (monitoreo y costo), estimable, pequeña y testeable.

## HU-030: Visualización del flujo de orquestación

**Como** administrador del sistema, **quiero** visualizar el flujo de la orquestación como diagrama Mermaid y JSON, **para** entender la secuencia y las dependencias de la ejecución.

**Reglas de negocio:**
- RN-126: El `FlowTracker` genera un diagrama Mermaid del DAG de ejecución.
- RN-127: La salida incluye también el resumen JSON del flujo.
- RN-128: El diagrama se devuelve en la respuesta de la auditoría (`mermaid_diagram`).

**Criterios de aceptación:**
- Dado que una auditoría se ejecuta con Strands, cuando se devuelve la respuesta, entonces incluye el diagrama Mermaid del flujo.
- Dado que el flujo tiene nodos en paralelo, cuando se genera el diagrama, entonces el DAG refleja las dependencias y el fan-out.

**Revisión INVEST:** Independiente, negociable (formato), valiosa (comprensión del flujo), estimable, pequeña y testeable.

---

# ÉPICA-08: Evaluaciones de cumplimiento

**Objetivo:** Gestionar evaluaciones de cumplimiento de aplicaciones o recursos específicos, con resultado de conformidad.

## HU-031: Crear una evaluación de cumplimiento

**Como** auditor, **quiero** crear una evaluación indicando nombre, versión ISO y recursos a evaluar, **para** medir el cumplimiento de una aplicación o servicio.

**Reglas de negocio:**
- RN-129: El nombre de la evaluación es obligatorio.
- RN-130: La versión ISO es obligatoria: `2022` (93 controles, 4 dominios) o `2013` (114 controles, 14 dominios).
- RN-131: Los recursos a evaluar pueden ser: repositorio GitHub, endpoint de API, código fuente, entre otros.
- RN-132: Al crearse, la evaluación queda en estado `pendiente` sin resultado.
- RN-133: La evaluación se asocia al tenant del usuario.

**Criterios de aceptación:**
- Dado que soy un auditor autenticado, cuando creo una evaluación con nombre, versión ISO y recursos, entonces el sistema la registra en estado `pendiente` y aparece en la lista.
- Dado que intento crear una evaluación sin nombre o versión ISO, cuando envío el formulario, entonces el sistema muestra un error de validación.

**Revisión INVEST:** Independiente, negociable (tipos de recursos), valiosa (mide cumplimiento por recurso), estimable, pequeña y testeable.

## HU-032: Listar evaluaciones y consultar su resultado

**Como** auditor, **quiero** ver la lista de evaluaciones con su estado y resultado, **para** dar seguimiento al cumplimiento de cada recurso.

**Reglas de negocio:**
- RN-134: La lista muestra: nombre, versión ISO, fecha de creación, fecha de actualización, estado y resultado.
- RN-135: El filtro por versión ISO admite `todas`, `2022` y `2013`.
- RN-136: El resultado es un puntaje de conformidad (0-100) que se muestra cuando la evaluación está completada.
- RN-137: La lista solo muestra evaluaciones del tenant del usuario.

**Criterios de aceptación:**
- Dado que tengo evaluaciones creadas, cuando entro a la sección Evaluaciones, entonces veo la tabla con nombre, versión, fechas, estado y resultado.
- Dado que una evaluación está completada, cuando se muestra su fila, entonces el resultado (puntaje) es visible.
- Dado que selecciono el filtro `ISO 27001:2013`, cuando aplico el filtro, entonces solo se muestran las evaluaciones con versión 2013.

**Revisión INVEST:** Independiente, negociable (columnas), valiosa (seguimiento), estimable, pequeña y testeable.

---

## Resumen de la revisión INVEST

| Épica | Historias | Mejoras INVEST aplicadas |
|---|---|---|
| ÉPICA-01: Autenticación | HU-001..004 | Historias divididas por capacidad (registro, login, tenant, rutas); cada una con criterios verificables contra Cognito |
| ÉPICA-02: Gestión de auditorías | HU-005..009 | Separadas creación, listado, detalle, eliminación y carga de datos; reglas de negocio derivadas del frontend y la API |
| ÉPICA-03: Pipeline SAST | HU-010..012 | Flujo completo dividido en subida, análisis y evaluación; criterios alineados a CodePipeline y S3 |
| ÉPICA-04: Sistema multi-agente | HU-013..019 | Una historia por agente (independencia y tamaño pequeño); la consolidación separa consistencia, veredicto y persistencia |
| ÉPICA-05: Multi-framework | HU-020..023 | Una historia por framework; criterios de aceptación por endpoint y comportamiento observable |
| ÉPICA-06: RAG | HU-024..027 | Separadas ingesta, chunking, embeddings y recuperación; criterios con métricas medibles (Recall@5, MRR) |
| ÉPICA-07: Observabilidad | HU-028..030 | Separadas trazabilidad, métricas y visualización; cada una testeable con salidas concretas |
| ÉPICA-08: Evaluaciones | HU-031..032 | Separadas creación y consulta; reglas de negocio del frontend |

**Total: 8 épicas, 32 historias de usuario.**

## Notas de trazabilidad

- Las historias HU-013 a HU-019 y HU-020 a HU-023 corresponden a los orquestadores `agentcore`, `strandsagents`, `langgraph`, `crewai` y `comp2013` del directorio `backend/`.
- Las historias HU-010 a HU-012 corresponden al pipeline SAST en `deliverables/pipeline/`.
- Las historias HU-024 a HU-027 corresponden al pipeline RAG en `actividad1.16/` y `src/rag/`.
- Las historias HU-001 a HU-009, HU-031 y HU-032 corresponden al frontend SPA en `frontend/` y a la plataforma en `fullstack-platform/`.
- Las historias HU-028 a HU-030 corresponden a `backend/observability/` y `backend/models/`.
- Los datos sintéticos de prueba (ACME Corp) están en `testsets/` y cubren los dominios A.5-A.8.