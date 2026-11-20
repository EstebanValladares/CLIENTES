/**
 * Módulo Vue: Proyectos y Permisos
 * Ubicación: vue/static/js/modules/proyectos.js
 * 
 * Gestiona la lista de usuarios protegidos, obras asignadas,
 * y la depuración automatizada de permisos vía Selenium/RPA.
 */

window.createProyectosModule = function(Vue) {
  const { ref, computed } = Vue;

  // Estado reactivo
  const permisosUsuarios = ref([]);
  const permisosObras = ref([]);
  const nuevoUsuarioProtegido = ref('');
  const nuevaObra = ref('');
  const terminalLiveContenido = ref('[Sistema preparado. Presione "Comenzar Depuración" para iniciar.]');
  const historialPermisosContenido = ref('');
  const ejecutandoDepuracion = ref(false);

  // ==========================================
  // ESTADO DESASIGNACIÓN DE USUARIOS POR OBRA
  // ==========================================
  const desasigData = ref({
    metadata: {},
    usuarios: [],
    lista_obras: [],
    por_obra: {},
    por_usuario: {}
  });
  const desasigCargando = ref(false);
  const ejecutandoDesasignacion = ref(false);
  const desasigModoPrueba = ref(true);
  const desasigLimiteObras = ref(1);
  const filtroDesasigUsuario = ref('');
  const filtroDesasigObra = ref('');
  const desasigUsuarioSeleccionado = ref('');
  const nuevoUsuarioDesasig = ref('');
  const nuevaObraDesasigClave = ref('');
  const nuevaObraDesasigNombre = ref('');

  // Cargar configuración de desasignación (Modo Prueba y Límite)
  const cargarConfigDesasignacion = async () => {
    try {
      const res = await fetch('/api/operaciones/desasignacion/config');
      if (res.ok) {
        const cfg = await res.json();
        if (cfg.modo_prueba !== undefined) desasigModoPrueba.value = Boolean(cfg.modo_prueba);
        if (cfg.limite_obras !== undefined) desasigLimiteObras.value = Number(cfg.limite_obras);
      }
    } catch (e) {
      console.error('Error cargando config desasignación:', e);
    }
  };

  const guardarConfigDesasignacion = async () => {
    try {
      await fetch('/api/operaciones/desasignacion/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          modo_prueba: desasigModoPrueba.value,
          limite_obras: desasigLimiteObras.value
        })
      });
    } catch (e) {
      console.error('Error guardando config desasignación:', e);
    }
  };

  // Cargar datos de desasignación
  const cargarDesasignacion = async () => {
    desasigCargando.value = true;
    try {
      const res = await fetch('/api/operaciones/desasignacion');
      if (res.ok) {
        desasigData.value = await res.json();
      }
      await cargarConfigDesasignacion();
    } catch (e) {
      console.error('Error cargando desasignación:', e);
    } finally {
      desasigCargando.value = false;
    }
  };

  // Guardar datos de desasignación en servidor
  const guardarDesasignacionServidor = async () => {
    try {
      await fetch('/api/operaciones/desasignacion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(desasigData.value)
      });
    } catch (e) {
      console.error('Error guardando desasignación en servidor:', e);
    }
  };

  // Gestión de usuarios en desasignación
  const agregarUsuarioDesasig = async () => {
    const val = nuevoUsuarioDesasig.value.trim().toUpperCase();
    if (!val) return;
    if (!desasigData.value.usuarios.includes(val)) {
      desasigData.value.usuarios.push(val);
      if (!desasigData.value.por_usuario[val]) {
        desasigData.value.por_usuario[val] = [];
      }
      await guardarDesasignacionServidor();
      nuevoUsuarioDesasig.value = '';
    }
  };

  const eliminarUsuarioDesasig = async (usuario) => {
    desasigData.value.usuarios = desasigData.value.usuarios.filter(u => u !== usuario);
    delete desasigData.value.por_usuario[usuario];
    Object.values(desasigData.value.por_obra).forEach(obra => {
      if (obra.usuarios) {
        obra.usuarios = obra.usuarios.filter(u => u !== usuario);
      }
    });
    if (desasigUsuarioSeleccionado.value === usuario) {
      desasigUsuarioSeleccionado.value = '';
    }
    await guardarDesasignacionServidor();
  };

  // Gestión de obras en desasignación
  const agregarObraDesasig = async () => {
    const cve = nuevaObraDesasigClave.value.trim().toUpperCase();
    const nom = nuevaObraDesasigNombre.value.trim() || cve;
    if (!cve) return;
    if (!desasigData.value.lista_obras.includes(cve)) {
      desasigData.value.lista_obras.unshift(cve);
      desasigData.value.por_obra[cve] = {
        proyecto: cve,
        nombre: nom,
        usuarios: [],
        id_proyecto: null,
        url_directa: null
      };
      await guardarDesasignacionServidor();
      nuevaObraDesasigClave.value = '';
      nuevaObraDesasigNombre.value = '';
    }
  };

  const eliminarObraDesasig = async (clave) => {
    desasigData.value.lista_obras = desasigData.value.lista_obras.filter(o => o !== clave);
    delete desasigData.value.por_obra[clave];
    Object.values(desasigData.value.por_usuario).forEach(obrasList => {
      const idx = obrasList.findIndex(o => o.proyecto === clave);
      if (idx !== -1) obrasList.splice(idx, 1);
    });
    await guardarDesasignacionServidor();
  };

  const toggleUsuarioFiltro = (usr) => {
    if (desasigUsuarioSeleccionado.value === usr) {
      desasigUsuarioSeleccionado.value = '';
    } else {
      desasigUsuarioSeleccionado.value = usr;
    }
  };

  const usuariosFiltradosDesasig = computed(() => {
    const q = filtroDesasigUsuario.value.trim().toUpperCase();
    const usrs = desasigData.value.usuarios || [];
    if (!q) return usrs;
    return usrs.filter(u => u.includes(q));
  });

  const obrasFiltradasDesasig = computed(() => {
    const q = filtroDesasigObra.value.trim().toUpperCase();
    const map = desasigData.value.por_obra || {};
    let entries = Object.values(map);

    if (desasigUsuarioSeleccionado.value) {
      entries = entries.filter(o => o.usuarios && o.usuarios.includes(desasigUsuarioSeleccionado.value));
    }

    if (q) {
      entries = entries.filter(o => {
        const cve = (o.proyecto || '').toUpperCase();
        const nom = (o.nombre || '').toUpperCase();
        const pid = String(o.id_proyecto || '');
        return cve.includes(q) || nom.includes(q) || pid.includes(q);
      });
    }

    return entries;
  });

  const textoBotonDesasignacion = computed(() => {
    if (ejecutandoDesasignacion.value) {
      return 'Desasignación en Curso...';
    }
    if (desasigModoPrueba.value) {
      if (desasigLimiteObras.value === 1) {
        return 'Ejecutar Prueba en 1 Obra (Sin Guardar)';
      }
      const cant = desasigLimiteObras.value === 0 ? 'Todas las' : desasigLimiteObras.value;
      return 'Ejecutar Prueba (' + cant + ' Obras - Sin Guardar)';
    }
    return 'Comenzar Desasignación Real (Guardar y Quitar)';
  });

  // Cargar permisos desde la API
  const cargarPermisos = async (intentos = 3) => {
    try {
      const res = await fetch('/api/operaciones/permisos');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      permisosUsuarios.value = data.usuarios_protegidos || [];
      permisosObras.value = data.obras || [];

      const resHist = await fetch('/api/operaciones/permisos/historial');
      if (resHist.ok) {
        const dataHist = await resHist.json();
        historialPermisosContenido.value = dataHist.log || '';
      }
    } catch (e) {
      console.error('Error cargando permisos:', e);
      if (intentos > 1) setTimeout(() => cargarPermisos(intentos - 1), 1200);
    }
  };

  // Guardar configuración de permisos en servidor
  const guardarPermisosServidor = async () => {
    try {
      await fetch('/api/operaciones/permisos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          usuarios_protegidos: permisosUsuarios.value,
          obras: permisosObras.value
        })
      });
    } catch (e) {
      console.error('Error guardando permisos en servidor:', e);
    }
  };

  // Gestión de usuarios protegidos
  const agregarUsuarioProtegido = async () => {
    const val = nuevoUsuarioProtegido.value.trim().toUpperCase();
    if (!val) return;
    if (!permisosUsuarios.value.includes(val)) {
      permisosUsuarios.value.push(val);
      await guardarPermisosServidor();
      nuevoUsuarioProtegido.value = '';
    }
  };

  const eliminarUsuarioProtegido = async (idx) => {
    permisosUsuarios.value.splice(idx, 1);
    await guardarPermisosServidor();
  };

  // Gestión de obras a depurar
  const agregarObra = async () => {
    const val = nuevaObra.value.trim().toUpperCase();
    if (!val) return;
    if (!permisosObras.value.includes(val)) {
      permisosObras.value.push(val);
      await guardarPermisosServidor();
      nuevaObra.value = '';
    }
  };

  const eliminarObra = async (idx) => {
    permisosObras.value.splice(idx, 1);
    await guardarPermisosServidor();
  };

  const cargarObrasDesdeJSON = (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const data = JSON.parse(e.target.result);
        if (Array.isArray(data)) {
          data.forEach(o => {
            const ob = String(o).trim().toUpperCase();
            if (ob && !permisosObras.value.includes(ob)) {
              permisosObras.value.push(ob);
            }
          });
          await guardarPermisosServidor();
        }
      } catch (err) {
        alert('Archivo JSON no válido.');
      }
    };
    reader.readAsText(file);
  };

  // Iniciar proceso Selenium
  const iniciarDepuracionPermisos = async () => {
    if (!permisosObras.value.length) {
      alert('Debes agregar al menos una obra antes de comenzar.');
      return;
    }

    await guardarPermisosServidor();

    ejecutandoDepuracion.value = true;
    terminalLiveContenido.value = '[Iniciando Selenium para la depuración de permisos en las obras indicadas...]\n';

    try {
      const resInit = await fetch('/api/bots/ejecutar/PROYECTOS', { method: 'POST' });
      const initData = await resInit.json();
      if (!resInit.ok) {
        terminalLiveContenido.value += `\n[ERROR]: ${initData.detail || 'Fallo al iniciar el bot.'}`;
        ejecutandoDepuracion.value = false;
        return;
      }

      const interval = setInterval(async () => {
        const res = await fetch('/api/bots/logs/PROYECTOS');
        const data = await res.json();
        if (data.logs && data.logs.length) {
          terminalLiveContenido.value = data.logs.join('\n');
          const el = document.getElementById('terminal-live');
          if (el) el.scrollTop = el.scrollHeight;
        }
        if (data.estado !== 'EJECUTANDO') {
          clearInterval(interval);
          ejecutandoDepuracion.value = false;
          await cargarPermisos();
        }
      }, 1000);
    } catch (e) {
      terminalLiveContenido.value += `\n[ERROR]: No se pudo conectar con el bot.`;
      ejecutandoDepuracion.value = false;
    }
  };

  // Iniciar proceso de Desasignación Automática con Selenium
  const iniciarDesasignacion = async () => {
    const totalObras = (desasigData.value.lista_obras || []).length;
    if (totalObras === 0) {
      alert('No hay obras pendientes en la lista de desasignación.');
      return;
    }

    await guardarConfigDesasignacion();

    const cantObrasTexto = desasigLimiteObras.value === 0 
      ? `todas las ${totalObras} obras pendientes` 
      : `${Math.min(desasigLimiteObras.value, totalObras)} obra(s)`;

    const msgConfirm = desasigModoPrueba.value
      ? `[MODO PRUEBA ACTIVO]\n\n¿Deseas ejecutar la prueba en ${cantObrasTexto} SIN GUARDAR cambios en Aryve?\n\nEl bot entrará a la obra, eliminará a los usuarios en pantalla para que lo compruebes visualmente, pero NO presionará Guardar.`
      : `[MODO REAL CON GUARDADO]\n\n¿Deseas ejecutar la desasignación en ${cantObrasTexto} GUARDANDO cambios en Aryve?\n\nLas obras procesadas exitosamente se eliminarán de la lista del Dashboard automáticamente.`;

    if (!confirm(msgConfirm)) {
      return;
    }

    ejecutandoDesasignacion.value = true;
    terminalLiveContenido.value = `[Iniciando Selenium: Desasignación de usuarios en ${cantObrasTexto} (${desasigModoPrueba.value ? 'MODO PRUEBA / SIN GUARDAR' : 'MODO REAL'})...]\n`;

    try {
      const resInit = await fetch('/api/bots/ejecutar/DESASIGNACION_PROYECTOS', { method: 'POST' });
      const initData = await resInit.json();
      if (!resInit.ok) {
        terminalLiveContenido.value += `\n[ERROR]: ${initData.detail || 'Fallo al iniciar el bot de desasignación.'}`;
        ejecutandoDesasignacion.value = false;
        return;
      }

      const interval = setInterval(async () => {
        const res = await fetch('/api/bots/logs/DESASIGNACION_PROYECTOS');
        const data = await res.json();
        if (data.logs && data.logs.length) {
          terminalLiveContenido.value = data.logs.join('\n');
          const el = document.getElementById('terminal-live');
          if (el) el.scrollTop = el.scrollHeight;
        }
        // En modo real, refrescamos el listado para ver las obras desaparecer
        if (!desasigModoPrueba.value) {
          await cargarDesasignacion();
        }
        if (data.estado !== 'EJECUTANDO') {
          clearInterval(interval);
          ejecutandoDesasignacion.value = false;
          await cargarDesasignacion();
        }
      }, 1200);
    } catch (e) {
      terminalLiveContenido.value += `\n[ERROR]: No se pudo conectar con el bot de desasignación.`;
      ejecutandoDesasignacion.value = false;
    }
  };

  return {
    permisosUsuarios,
    permisosObras,
    nuevoUsuarioProtegido,
    nuevaObra,
    terminalLiveContenido,
    historialPermisosContenido,
    ejecutandoDepuracion,
    cargarPermisos,
    guardarPermisosServidor,
    agregarUsuarioProtegido,
    eliminarUsuarioProtegido,
    agregarObra,
    eliminarObra,
    cargarObrasDesdeJSON,
    iniciarDepuracionPermisos,

    // Desasignación de usuarios por proyecto
    desasigData,
    desasigCargando,
    ejecutandoDesasignacion,
    desasigModoPrueba,
    desasigLimiteObras,
    filtroDesasigUsuario,
    filtroDesasigObra,
    desasigUsuarioSeleccionado,
    nuevoUsuarioDesasig,
    nuevaObraDesasigClave,
    nuevaObraDesasigNombre,
    cargarDesasignacion,
    guardarDesasignacionServidor,
    cargarConfigDesasignacion,
    guardarConfigDesasignacion,
    agregarUsuarioDesasig,
    eliminarUsuarioDesasig,
    agregarObraDesasig,
    eliminarObraDesasig,
    toggleUsuarioFiltro,
    usuariosFiltradosDesasig,
    obrasFiltradasDesasig,
    textoBotonDesasignacion,
    iniciarDesasignacion
  };
};
