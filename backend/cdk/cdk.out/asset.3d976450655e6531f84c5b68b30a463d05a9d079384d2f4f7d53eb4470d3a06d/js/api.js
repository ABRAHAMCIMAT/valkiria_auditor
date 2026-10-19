/**
 * API Client para Auditor Lead
 * Maneja la comunicación con el backend y datos mock para demo
 */
const API = (() => {
  // Configuración del endpoint base (vacío = modo demo con datos mock)
  const BASE_URL = window.__API_BASE_URL__ || '';

  // ===== Datos Mock =====
  const mockAuditorias = [
    {
      id: 1,
      nombre: 'Auditoria Empresa A',
      creada: '2025-03-10',
      actualizacion: '2025-05-14',
      completada: '2025-05-14',
      isoVersion: '2022',
      estado: 'completada',
      framework: 'strands'
    },
    {
      id: 2,
      nombre: 'Auditoria proyecto mercantiles',
      creada: '2025-04-01',
      actualizacion: '2025-06-01',
      completada: null,
      isoVersion: '2022',
      estado: 'en_progreso',
      framework: 'langgraph'
    },
    {
      id: 3,
      nombre: 'Auditoria backend de servicios',
      creada: '2025-05-15',
      actualizacion: '2025-05-20',
      completada: null,
      isoVersion: '2013',
      estado: 'pendiente',
      framework: 'comp2013'
    }
  ];

  const mockEvaluaciones = [
    {
      id: 1,
      nombre: 'Evaluación App Financiera',
      creada: '2025-02-20',
      actualizacion: '2025-04-10',
      estado: 'completada',
      isoVersion: '2022',
      recursos: ['repo-github', 'endpoint-api'],
      resultado: 85
    },
    {
      id: 2,
      nombre: 'Evaluación Microservicios',
      creada: '2025-05-01',
      actualizacion: '2025-05-25',
      estado: 'en_progreso',
      isoVersion: '2013',
      recursos: ['codigo-fuente'],
      resultado: null
    }
  ];

  const mockAuditoriaDetalle = {
    id: 1,
    nombre: 'Auditoria Empresa A',
    creada: '2025-03-10',
    actualizacion: '2025-05-14',
    completada: '2025-05-14',
    isoVersion: '2022',
    estado: 'completada',
    framework: 'strands',
    progreso: 100,
    hallazgos: [
      { id: 1, control: 'A.5.1', descripcion: 'Políticas de seguridad no actualizadas', severidad: 'alta', estado: 'abierto' },
      { id: 2, control: 'A.6.2', descripcion: 'Falta capacitación en seguridad', severidad: 'media', estado: 'en_remediacion' },
      { id: 3, control: 'A.8.1', descripcion: 'Inventario de activos incompleto', severidad: 'alta', estado: 'abierto' },
      { id: 4, control: 'A.9.4', descripcion: 'Control de acceso débil en sistemas legacy', severidad: 'alta', estado: 'cerrado' },
      { id: 5, control: 'A.12.3', descripcion: 'Backups sin verificación periódica', severidad: 'media', estado: 'cerrado' },
      { id: 6, control: 'A.14.1', descripcion: 'Requisitos de seguridad no documentados', severidad: 'baja', estado: 'cerrado' }
    ],
    agentes: [
      { nombre: 'Agente Controles Organizacionales', estado: 'completado', controles_evaluados: 37 },
      { nombre: 'Agente Controles de Personas', estado: 'completado', controles_evaluados: 8 },
      { nombre: 'Agente Controles Físicos', estado: 'completado', controles_evaluados: 14 },
      { nombre: 'Agente Controles Tecnológicos', estado: 'completado', controles_evaluados: 34 }
    ],
    resumen: {
      total_controles: 93,
      conformes: 78,
      no_conformes: 10,
      parcialmente_conformes: 5
    }
  };

  // ===== Helpers =====
  async function request(method, path, body = null) {
    if (!BASE_URL) {
      return mockResponse(method, path, body);
    }

    const options = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${BASE_URL}${path}`, options);

    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  function mockResponse(method, path, body) {
    return new Promise((resolve) => {
      setTimeout(() => {
        if (path.includes('/auditorias') && method === 'GET' && !path.includes('/auditorias/')) {
          resolve([...mockAuditorias]);
        } else if (path.match(/\/auditorias\/\d+/) && method === 'GET') {
          resolve({ ...mockAuditoriaDetalle });
        } else if (path.includes('/auditorias') && method === 'POST') {
          const newAuditoria = {
            id: mockAuditorias.length + 1,
            ...body,
            creada: new Date().toISOString().split('T')[0],
            actualizacion: new Date().toISOString().split('T')[0],
            completada: null,
            estado: 'pendiente'
          };
          mockAuditorias.push(newAuditoria);
          resolve(newAuditoria);
        } else if (path.includes('/auditorias') && method === 'DELETE') {
          resolve({ success: true });
        } else if (path.includes('/evaluaciones') && method === 'GET') {
          resolve([...mockEvaluaciones]);
        } else if (path.includes('/evaluaciones') && method === 'POST') {
          const newEval = {
            id: mockEvaluaciones.length + 1,
            ...body,
            creada: new Date().toISOString().split('T')[0],
            actualizacion: new Date().toISOString().split('T')[0],
            estado: 'pendiente',
            resultado: null
          };
          mockEvaluaciones.push(newEval);
          resolve(newEval);
        } else if (path.includes('/audit/strands') || path.includes('/audit/langgraph') || path.includes('/audit/crewai')) {
          resolve({ status: 'ejecutando', agente: path.split('/').pop(), mensaje: 'Auditoría ISO 27001:2022 iniciada' });
        } else if (path.includes('/audit/comp2013')) {
          resolve({ status: 'ejecutando', mensaje: 'Auditoría ISO 27001:2013 iniciada' });
        } else {
          resolve({});
        }
      }, 300);
    });
  }

  // ===== API Pública =====
  return {
    // Auditorías
    getAuditorias() {
      return request('GET', '/auditorias');
    },

    getAuditoria(id) {
      return request('GET', `/auditorias/${id}`);
    },

    createAuditoria(data) {
      return request('POST', '/auditorias', data);
    },

    deleteAuditoria(id) {
      return request('DELETE', `/auditorias/${id}`);
    },

    // Ejecutar auditoría según versión ISO
    ejecutarAuditoria(isoVersion, framework = 'strands') {
      if (isoVersion === '2013') {
        return request('POST', '/audit/comp2013');
      }
      // ISO 2022 - seleccionar framework
      return request('POST', `/audit/${framework}`);
    },

    // Evaluaciones
    getEvaluaciones() {
      return request('GET', '/evaluaciones');
    },

    createEvaluacion(data) {
      return request('POST', '/evaluaciones', data);
    },

    // Configuración
    getBaseUrl() {
      return BASE_URL;
    }
  };
})();
