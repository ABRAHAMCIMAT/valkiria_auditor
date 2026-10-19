# Evaluacion de Controles Fisicos (A.7) — ACME Corp

**Organizacion:** ACME Corp S.A. de C.V.
**Periodo de evaluacion:** Julio 2024 – Junio 2025
**Evaluador:** Ing. Pedro Gutierrez, Gerente de Instalaciones
**Fecha del documento:** 2025-06-17
**Ubicaciones evaluadas:** 3 (CDMX Corporativo, GDL Desarrollo, MTY Soporte)

---

## A.7.1 — Perimetros de Seguridad Fisica

### Descripcion de Instalaciones

| Ubicacion | Tipo | Area (m2) | Personal | Nivel de Seguridad |
|-----------|------|-----------|----------|-------------------|
| CDMX — Torre Reforma 115, Piso 8 | Oficinas corporativas | 850 | 65 | Alto |
| GDL — Puerta de Hierro Business Park, Ed. B | Centro de desarrollo | 420 | 38 | Medio-Alto |
| MTY — Valle Oriente, Piso 3 | Centro de soporte | 280 | 17 | Medio |

### Controles Perimetrales por Ubicacion

**CDMX (Corporativo):**
- Edificio con control de acceso en planta baja (recepcion 24/7)
- Torniquetes con tarjeta de proximidad en lobby
- Piso 8 con puerta de acceso controlada (lector de tarjeta RFID)
- Recepcion propia en piso con registro de visitantes
- CCTV: 12 camaras (accesos, pasillos, areas comunes)
- Detector de intrusos: alarma perimetral fuera de horario (activacion automatica 21:00-07:00)

**GDL (Desarrollo):**
- Edificio compartido con control de acceso vehicular (pluma con tag)
- Acceso peatonal con vigilancia 24/7 en lobby principal
- Puerta de oficina con lector biometrico (huella dactilar)
- CCTV: 8 camaras (acceso principal, sala de servidores, estacionamiento)
- Sin alarma perimetral independiente (depende de sistema del edificio)

**MTY (Soporte):**
- Edificio comercial con recepcion compartida (horario 07:00-20:00)
- Puerta de oficina con cerradura electronica (codigo PIN + tarjeta)
- CCTV: 4 camaras (acceso, area de trabajo, sala de juntas)
- Sin vigilancia nocturna propia (depende de administracion del edificio)

### Hallazgos

- **No conformidad menor (MTY):** Fuera de horario de oficina (20:00-07:00), no existe control de acceso fisico al piso donde se ubican las oficinas. La puerta del edificio permanece accesible para otros inquilinos. Solo la puerta de la oficina con PIN protege el acceso.
- **Observacion (GDL):** El sistema de alarma perimetral depende del proveedor del edificio. ACME Corp no tiene acceso a configuracion ni registros del sistema. No existe SLA documentado con la administracion del edificio para respuesta a alertas.

---

## A.7.2 — Controles de Entrada Fisica

### Sistemas de Control de Acceso

| Ubicacion | Tecnologia | Registros | Revision | Integracion |
|-----------|-----------|-----------|----------|-------------|
| CDMX | RFID HID iCLASS SE | Si, 12 meses | Mensual | Integrado con RRHH (altas/bajas) |
| GDL | Biometrico ZKTeco + RFID | Si, 6 meses | Trimestral | Parcial (manual para bajas) |
| MTY | PIN + tarjeta Kaba | Si, 3 meses | No programada | No integrado |

### Gestion de Tarjetas/Credenciales

| Metrica | CDMX | GDL | MTY |
|---------|------|-----|-----|
| Tarjetas activas | 72 | 42 | 20 |
| Tarjetas de personal activo | 65 | 38 | 17 |
| Tarjetas sin asignar/temporales | 5 | 2 | 2 |
| Tarjetas posiblemente huerfanas | 2 | 2 | 1 |
| Tarjetas reportadas como perdidas (periodo) | 4 | 1 | 0 |
| Desactivacion inmediata tras reporte | 4/4 | 1/1 | N/A |

### Registro de Visitantes

- CDMX: Registro electronico en tablet (nombre, empresa, anfitrion, hora entrada/salida, foto)
- GDL: Registro en bitacora fisica + credencial de visitante temporal
- MTY: Registro en bitacora fisica (sin credencial de visitante)

### Hallazgos

- **No conformidad menor:** Se identificaron 5 tarjetas de acceso activas que no corresponden a personal vigente (2 CDMX, 2 GDL, 1 MTY). Posiblemente pertenecen a exempleados cuya baja no fue comunicada oportunamente al equipo de seguridad fisica.
- **No conformidad menor (MTY):** No se emite credencial de visitante temporal. Los visitantes transitan sin identificacion visible, dificultando distinguirlos del personal autorizado.
- **Observacion:** El sistema de GDL no esta integrado automaticamente con RRHH. Las bajas se procesan manualmente con un desfase de 1-5 dias habiles.

---

## A.7.3 — Seguridad de Oficinas, Salas e Instalaciones

### Areas de Acceso Restringido

| Area | Ubicacion | Control Adicional | Acceso Autorizado |
|------|-----------|-------------------|-------------------|
| Sala de servidores (IDF) | CDMX, Piso 8 | Biometrico + PIN | 4 personas (equipo infra) |
| Cuarto de comunicaciones | GDL | Llave fisica + registro | 3 personas (TI local) |
| Archivo fisico confidencial | CDMX | Llave + registro manual | 2 personas (Legal + RRHH) |
| UPS / Cuarto electrico | CDMX | Llave fisica | 2 personas (Facilities) |
| Laboratorio de pruebas | GDL | Tarjeta RFID | 8 personas (QA + Dev) |

### Evaluacion de Sala de Servidores (CDMX)

| Aspecto | Estado | Observacion |
|---------|--------|-------------|
| Control de acceso biometrico | Operativo | Registro de todos los accesos |
| Deteccion de incendio | Operativo | Sistema FM-200, inspeccion anual vigente |
| Control de temperatura | Operativo | 2 unidades de precision, monitoreo 24/7 |
| Deteccion de humedad | Operativo | Sensores bajo piso tecnico |
| UPS | Operativo | APC Smart-UPS 10kVA, autonomia 25 min |
| Planta de emergencia | No aplica | Depende de planta del edificio (SLA 15 min) |
| Piso elevado | Si | Cableado estructurado bajo piso |
| CCTV dedicado | Si | 2 camaras, grabacion 30 dias |
| Politica de acompanamiento | Documentada | Visitantes siempre escoltados |

### Hallazgos

- **Observacion:** El cuarto de comunicaciones de GDL no cuenta con deteccion de incendio independiente. Depende del sistema general del edificio cuya inspeccion no ha sido verificada por ACME Corp.
- **Observacion:** La sala de servidores no tiene redundancia electrica propia (depende de planta del edificio). Si la planta del edificio falla, la autonomia real es solo 25 minutos de UPS.

---

## A.7.4 — Monitoreo de Seguridad Fisica

### Sistemas de CCTV

| Ubicacion | Camaras | Grabacion | Retencion | Monitoreo | Estado |
|-----------|---------|-----------|-----------|-----------|--------|
| CDMX | 12 | Continua 24/7 | 30 dias | Tiempo real (recepcion) + grabacion | Operativo |
| GDL | 8 | Continua 24/7 | 15 dias | Solo grabacion (sin monitoreo en vivo) | Operativo |
| MTY | 4 | Continua 24/7 | 7 dias | Solo grabacion | Parcial (1 camara fuera de servicio) |

### Inspecciones de Seguridad Fisica

| Tipo de Inspeccion | Frecuencia | Ultima Realizada | Resultado |
|-------------------|-----------|------------------|-----------|
| Ronda de vigilancia (CDMX) | Diaria | 2025-06-17 | Sin novedades |
| Verificacion de cerraduras y accesos | Mensual | 2025-06-01 | 1 cerradura con falla (reparada) |
| Prueba de alarma de intrusos | Trimestral | 2025-04-15 | Operativa |
| Inspeccion de CCTV (funcionamiento) | Mensual | 2025-06-05 | 1 camara MTY fuera de servicio |
| Simulacro de evacuacion | Semestral | 2025-03-20 | Completado en 4.5 min (meta: 5 min) |
| Revision de extintores | Anual | 2025-01-15 | Todos vigentes |

### Hallazgos

- **No conformidad menor (MTY):** Una camara de CCTV en el area de trabajo lleva fuera de servicio desde el 5 de mayo 2025 (43 dias). No se ha generado orden de reparacion ni se ha implementado control compensatorio.
- **Observacion (GDL):** No existe monitoreo en tiempo real de CCTV. Las grabaciones solo se revisan en caso de incidente. Un evento de seguridad podria no detectarse hasta que alguien revise las grabaciones.
- **Observacion:** La retencion de 7 dias en MTY es insuficiente para investigaciones que pueden iniciarse semanas despues de un evento.

---

## A.7.5 — Proteccion contra Amenazas Fisicas y Ambientales

### Evaluacion de Riesgos Ambientales

| Amenaza | Probabilidad | Impacto | Controles Existentes | Residual |
|---------|-------------|---------|---------------------|----------|
| Sismo (CDMX zona sismica) | Alta | Alto | Edificio con normas sismicas, plan de evacuacion, simulacros | Medio |
| Inundacion (GDL temporada lluvias) | Media | Medio | Piso elevado en servidores, drenaje verificado | Bajo |
| Incendio | Baja | Critico | FM-200, extintores, detectores de humo, rutas de evacuacion | Bajo |
| Falla electrica prolongada | Media | Alto | UPS (25 min), planta de edificio (SLA 15 min) | Medio |
| Temperatura extrema en sala servidores | Baja | Alto | 2 unidades de clima, alertas automaticas | Bajo |

### Controles Ambientales Implementados

- Detectores de humo en todas las areas (revisados anualmente)
- Extintores tipo ABC cada 15 metros (vigentes, proxima recarga: enero 2026)
- Sistema FM-200 en sala de servidores (ultima inspeccion: enero 2025)
- Sensores de temperatura y humedad con alertas via SMS/email
- Rutas de evacuacion senalizadas y actualizadas
- Brigada de emergencia capacitada (12 brigadistas)

### Hallazgos

- **Observacion:** No se ha realizado un analisis formal de impacto por falla electrica prolongada (>4 horas) en ninguna ubicacion. El escenario de falla simultanea de UPS + planta del edificio no tiene plan de contingencia documentado.
- **Positivo:** Los simulacros de evacuacion se realizan conforme al programa y los tiempos estan dentro de metas.

---

## A.7.6 — Trabajo en Areas Seguras

### Reglas para Areas Seguras

**Sala de Servidores (CDMX):**
- Acceso solo para personal autorizado (lista de 4 personas)
- Visitantes/proveedores siempre acompanados y registrados en bitacora
- Prohibido alimentos, bebidas y materiales inflamables
- Prohibido equipo fotografico o de grabacion (salvo autorizacion escrita)
- Trabajo supervisado por al menos un miembro del equipo de infraestructura

**Archivo Confidencial (CDMX):**
- Acceso restringido a Legal y RRHH
- Material no sale del area sin registro y autorizacion
- Destruccion de documentos solo con servicio certificado (cross-cut, nivel P-4)

### Hallazgos

- **Observacion:** No existe registro de acompanamiento para los tecnicos del proveedor de aire acondicionado que dan mantenimiento trimestral a la sala de servidores. El tecnico tiene acceso fisico al equipo de computo durante el servicio sin supervision continua documentada.

---

## A.7.7 — Escritorio y Pantalla Limpia

### Politica de Escritorio Limpio

- Documentos confidenciales deben guardarse en cajon con llave al ausentarse
- Pantallas deben bloquearse al alejarse del puesto (Windows+L / Command+Control+Q)
- Bloqueo automatico configurado a 5 minutos de inactividad
- Pizarrones y notas adhesivas con informacion sensible deben borrarse al terminar reunion
- Impresiones deben recogerse inmediatamente (impresion segura con PIN)

### Resultados de Inspecciones Sorpresa

| Fecha | Ubicacion | Escritorios revisados | Violaciones detectadas | Tipo de Violacion |
|-------|-----------|----------------------|----------------------|-------------------|
| 2024-09-12 | CDMX | 30 | 8 | 4 doc. expuestos, 2 pantallas sin bloquear, 2 cajones abiertos |
| 2024-12-05 | GDL | 20 | 5 | 3 doc. expuestos, 1 pantalla sin bloquear, 1 nota con contrasena |
| 2025-03-18 | CDMX | 28 | 4 | 2 doc. expuestos, 1 pantalla sin bloquear, 1 USB expuesta |
| 2025-06-10 | MTY | 15 | 6 | 3 doc. expuestos, 2 pantallas sin bloquear, 1 nota con credenciales |

**Tasa de violacion promedio:** 18.3% de escritorios inspeccionados presentan al menos una violacion.

### Hallazgos

- **No conformidad menor:** La tasa de violaciones permanece por encima del 15% a pesar de campanas de concientizacion. Especial preocupacion por 2 casos de contrasenas escritas en notas adhesivas visibles (GDL diciembre 2024 y MTY junio 2025).
- **Observacion:** No existe consecuencia formal documentada para violaciones reiteradas de la politica de escritorio limpio. Las acciones se limitan a recordatorios por correo.

---

## A.7.8 — Ubicacion y Proteccion de Equipos

### Inventario de Equipos Criticos

| Equipo | Ubicacion | Proteccion | Responsable |
|--------|-----------|-----------|-------------|
| Servidor de base de datos (Dell R750) | CDMX, Sala servidores, Rack A1 | Acceso biometrico, UPS, clima controlado | Ing. R. Sanchez |
| Servidor de aplicaciones (Dell R650) | CDMX, Sala servidores, Rack A2 | Acceso biometrico, UPS, clima controlado | Ing. R. Sanchez |
| Switch core (Cisco Catalyst 9300) | CDMX, Sala servidores, Rack B1 | Acceso biometrico, UPS | Ing. L. Herrera |
| Firewall (Fortinet 200F) | CDMX, Sala servidores, Rack B1 | Acceso biometrico, UPS | Ing. L. Herrera |
| NAS Backup (Synology RS3621) | CDMX, Sala servidores, Rack C1 | Acceso biometrico, UPS | Ing. R. Sanchez |
| Switch de distribucion (GDL) | GDL, Cuarto comunicaciones | Llave fisica, UPS pequeno | Ing. M. Ochoa |
| Access Point (15 unidades) | Distribuidos en 3 ubicaciones | Montaje en techo, sin proteccion adicional | TI local |

### Hallazgos

- **Observacion:** Los access points estan montados en techos de areas comunes sin proteccion anti-manipulacion (tamper). Un actor malicioso podria desconectar o sustituir un AP sin que se detecte inmediatamente.
- **Positivo:** Los equipos criticos en la sala de servidores cuentan con proteccion adecuada contra amenazas fisicas y ambientales.

---

## A.7.9 — Seguridad de Activos Fuera de las Instalaciones

### Equipos Portatiles

| Tipo | Cantidad | Cifrado | Rastreo | Borrado Remoto |
|------|----------|---------|---------|----------------|
| Laptops corporativas | 95 | BitLocker/FileVault (100%) | No | Parcial (solo 60% con MDM) |
| Telefonos corporativos | 25 | Cifrado nativo iOS/Android | Find My / Find My Device | Si (100%) |
| Tablets | 8 | Cifrado nativo | No | No |
| Discos externos cifrados | 12 | Hardware encryption | No | N/A |

### Hallazgos

- **No conformidad menor:** 38 laptops corporativas (40%) no tienen capacidad de borrado remoto ni rastreo por falta de MDM. En caso de perdida o robo, el unico control es el cifrado de disco.
- **Observacion:** Las tablets (usadas en demostraciones a clientes) no tienen rastreo ni borrado remoto. 2 tablets fueron reportadas como extraviadas en el periodo sin posibilidad de realizar wipe remoto.

---

## A.7.10 — Medios de Almacenamiento

### Gestion del Ciclo de Vida

| Medio | En uso | En almacen | Destruidos (periodo) | Metodo de Destruccion |
|-------|--------|-----------|---------------------|----------------------|
| Discos HDD (servidores retirados) | 0 | 4 | 8 | Degaussing + destruccion fisica (certificado) |
| SSD (laptops retiradas) | 0 | 6 | 3 | Borrado criptografico (no destruccion fisica) |
| USB corporativos cifrados | 12 | 5 | 2 | Borrado seguro (3 pasadas) |
| Cintas de backup (LTO) | 8 | 4 | 0 | N/A (aun en ciclo de retencion) |
| Documentos papel (cajas) | N/A | 12 cajas | 45 cajas | Cross-cut P-4 (proveedor DataGuard MX) |

### Hallazgos

- **Observacion:** Los 6 SSD en almacen (de laptops retiradas en abril 2025) no han sido procesados para destruccion segura. Permanecen en un cajon cerrado con llave en la sala de servidores, pero no se ha ejecutado el borrado criptografico ni la destruccion.
- **No conformidad menor:** No se cuenta con certificado de destruccion del proveedor DataGuard MX para los lotes de documentos de Q3 2024 (15 cajas). El proveedor confirmo destruccion verbal pero no ha entregado certificado escrito a la fecha.

---

## A.7.11 — Servicios de Soporte (Utilities)

### Infraestructura Electrica

| Componente | Ubicacion | Capacidad | Estado | Ultima Prueba |
|-----------|-----------|-----------|--------|---------------|
| UPS sala de servidores | CDMX | 10 kVA / 25 min autonomia | Operativo | 2025-05-15 |
| UPS cuarto comunicaciones | GDL | 3 kVA / 15 min autonomia | Operativo | 2025-04-20 |
| Reguladores de voltaje (oficinas) | Todas | Individual por rack/equipo | Operativo | N/A |
| Planta de emergencia | CDMX (edificio) | Compartida, SLA 15 min arranque | No verificado | No consta |

### Hallazgos

- **No conformidad menor:** No se ha verificado la capacidad ni el tiempo de arranque real de la planta de emergencia del edificio CDMX. El SLA contractual indica 15 minutos, pero no existe registro de prueba de transferencia con carga real. La administracion del edificio no proporciona reportes de mantenimiento.
- **Observacion (MTY):** La oficina de Monterrey no cuenta con UPS. Los equipos de red y estaciones de trabajo estan conectados directamente a la toma electrica regulada. Una falla electrica causaria perdida inmediata de servicio y posible corrupcion de datos.

---

## A.7.12 — Seguridad del Cableado

### Estado del Cableado

| Ubicacion | Tipo | Certificacion | Estado | Ultima Inspeccion |
|-----------|------|---------------|--------|-------------------|
| CDMX | Cat 6A, fibra monomodo | Si (Fluke certificado) | Bueno | 2024-08-10 |
| GDL | Cat 6, fibra multimodo | Si (parcial, 70%) | Aceptable | 2024-11-15 |
| MTY | Cat 5e | No | Regular | No consta |

### Hallazgos

- **Observacion (MTY):** El cableado Cat 5e no esta certificado y en inspeccion visual se observan cables expuestos en canaleta abierta, sin identificacion ni etiquetado. No se cuenta con diagrama de cableado actualizado.
- **Observacion (GDL):** El 30% de los puntos de red no tienen certificacion. Se identificaron 3 cables sin etiquetar en el cuarto de comunicaciones.

---

## A.7.13 — Mantenimiento de Equipos

### Programa de Mantenimiento

| Equipo/Sistema | Frecuencia | Proveedor | Ultimo Mantenimiento | Proximo |
|---------------|-----------|-----------|---------------------|---------|
| Servidores (CDMX) | Semestral | Dell ProSupport | 2025-03-10 | 2025-09-10 |
| UPS (CDMX) | Anual | APC/Schneider | 2025-01-20 | 2026-01-20 |
| Clima (Sala servidores) | Trimestral | ClimaTech MX | 2025-04-15 | 2025-07-15 |
| CCTV | Semestral | SecurVision | 2025-02-28 | 2025-08-28 |
| Control de acceso | Anual | HID Global Partner | 2024-12-01 | 2025-12-01 |
| Extintores | Anual | ProFire SA | 2025-01-15 | 2026-01-15 |
| FM-200 | Anual | ProFire SA | 2025-01-15 | 2026-01-15 |

### Hallazgos

- **Positivo:** El programa de mantenimiento preventivo esta documentado y se ejecuta dentro de los plazos establecidos para equipos criticos.
- **Observacion:** No existe programa de mantenimiento para equipos de red (switches, routers, access points) mas alla de actualizaciones de firmware por el equipo de TI.

---

## A.7.14 — Eliminacion o Reutilizacion Segura de Equipos

### Proceso de Baja de Equipos

1. Solicitud de baja por el responsable del activo
2. Respaldo de informacion relevante (si aplica)
3. Borrado seguro (NIST 800-88 Revision 1):
   - HDD: Borrado con 3 pasadas + verificacion, o degaussing + destruccion
   - SSD: Borrado criptografico (Secure Erase / Sanitize command)
   - Moviles: Factory reset + verificacion
4. Certificado de destruccion/borrado emitido
5. Actualizacion de inventario de activos
6. Disposicion final (reciclaje electronico certificado o donacion sin datos)

### Equipos Procesados en el Periodo

| Tipo | Cantidad | Metodo | Certificado | Destino |
|------|----------|--------|-------------|---------|
| Laptops | 12 | Borrado criptografico SSD | Si | Donacion (programa escuelas) |
| Desktops | 5 | Borrado 3 pasadas HDD | Si | Reciclaje electronico |
| Servidores retirados | 2 | Degaussing + destruccion fisica | Si | Reciclaje certificado |
| Impresoras | 3 | Borrado de memoria interna | No | Reciclaje |
| Telefonos moviles | 8 | Factory reset | Si (parcial) | Reutilizacion interna |

### Hallazgos

- **No conformidad menor:** 3 impresoras multifuncionales fueron enviadas a reciclaje sin borrado certificado de la memoria interna/disco duro. Las impresoras almacenan copias de documentos impresos/escaneados que podrian contener informacion confidencial.
- **Observacion:** El proceso de factory reset para telefonos no incluye verificacion posterior de que los datos fueron efectivamente eliminados.

---

## Resumen de Hallazgos por Control

| Control | Estado | No Conformidades | Observaciones |
|---------|--------|-----------------|---------------|
| A.7.1 Perimetros de seguridad | Parcialmente conforme | 1 menor | 1 |
| A.7.2 Controles de entrada | Parcialmente conforme | 2 menores | 1 |
| A.7.3 Oficinas y salas | Conforme | 0 | 2 |
| A.7.4 Monitoreo fisico | Parcialmente conforme | 1 menor | 2 |
| A.7.5 Amenazas ambientales | Conforme | 0 | 1 |
| A.7.6 Areas seguras | Conforme | 0 | 1 |
| A.7.7 Escritorio limpio | Parcialmente conforme | 1 menor | 1 |
| A.7.8 Ubicacion de equipos | Conforme | 0 | 1 |
| A.7.9 Activos fuera de instalaciones | Parcialmente conforme | 1 menor | 1 |
| A.7.10 Medios de almacenamiento | Parcialmente conforme | 1 menor | 1 |
| A.7.11 Servicios de soporte | Parcialmente conforme | 1 menor | 1 |
| A.7.12 Cableado | Parcialmente conforme | 0 | 2 |
| A.7.13 Mantenimiento | Conforme | 0 | 1 |
| A.7.14 Eliminacion segura | Parcialmente conforme | 1 menor | 1 |

**Total:** 10 no conformidades menores, 17 observaciones de mejora.

---

*Documento clasificado como: INTERNO*
*Preparado por Gerencia de Instalaciones para revision en Comite de Seguridad — Sesion del 25 de junio 2025*
