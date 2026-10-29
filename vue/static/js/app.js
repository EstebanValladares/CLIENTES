const { createApp, ref, computed, onMounted } = Vue;

createApp({
  setup() {
    // NAVEGACIÓN DE VISTAS (USUARIOS / PROYECTOS)
    const vistaActiva = ref('USUARIOS');

    // ESTADO GENERAL
    const cargando = ref(false);
    const usuarios = ref([]);
    const usuarioSeleccionado = ref(null);
    const filtroBusqueda = ref('');
    const filtroVigencia = ref('TODOS');
    const catalogoPuestos = ref([]);

    // BUSCADORES REACTIVOS DE PUESTOS / POSICIONES (230 posiciones)
    const busquedaPuestoNuevoUsuario = ref('');
    const mostrarDropdownPuestoNuevoUsuario = ref(false);

    const puestosFiltradosNuevoUsuario = computed(() => {
      const q = busquedaPuestoNuevoUsuario.value.trim().toLowerCase();
      if (!q) return catalogoPuestos.value;
      return catalogoPuestos.value.filter(p => p.toLowerCase().includes(q));
    });

    const seleccionarPuestoNuevoUsuario = (p) => {
      formUsuario.value.puesto = p;
      busquedaPuestoNuevoUsuario.value = p;
      mostrarDropdownPuestoNuevoUsuario.value = false;
    };

    const limpiarPuestoNuevoUsuario = () => {
      formUsuario.value.puesto = '';
      busquedaPuestoNuevoUsuario.value = '';
      mostrarDropdownPuestoNuevoUsuario.value = true;
    };

    const busquedaPuestoClasificador = ref('');
    const mostrarDropdownPuestoClasificador = ref(false);

    const puestosFiltradosClasificador = computed(() => {
      const q = busquedaPuestoClasificador.value.trim().toLowerCase();
      if (!q) return catalogoPuestos.value;
      return catalogoPuestos.value.filter(p => p.toLowerCase().includes(q));
    });

    const seleccionarPuestoModalClasificador = async (p) => {
      puestoClasificadorTemporal.value = p;
      busquedaPuestoClasificador.value = p;
      mostrarDropdownPuestoClasificador.value = false;
      await alCambiarPuestoModalClasificador();
    };

    const limpiarPuestoModalClasificador = () => {
      puestoClasificadorTemporal.value = '';
      busquedaPuestoClasificador.value = '';
      mostrarDropdownPuestoClasificador.value = true;
      infoClasificadorTemporal.value = { total: 0, area: '', categorias: [], clasificadores: {} };
    };

    
    // ==========================================
    // ESTADO OBRAS & WBS (ALTO RENDIMIENTO O(1))
    // ==========================================
    const metricasObras = ref({
      total_obras: 268,
      total_frentes: 2970,
      total_partidas: 12892,
      total_tarjetas: 89534,
      fecha_extraccion: ''
    });
    const obrasCatalogo = ref([]);
    const cargandoObras = ref(false);
    const cargandoArbolObra = ref(false);
    const sincronizandoObras = ref(false);
    const filtroBusquedaObra = ref('');
    const obraSeleccionada = ref(null);
    const arbolObraActual = ref(null);
    const filtroArbolObra = ref('');
    const cacheArbolesObras = new Map();
    const frentesExpandidos = ref({});
    const partidasExpandidas = ref({});

    const metricas = ref({
      total_usuarios: 0,
      total_bots: 0,
      total_ejecuciones: 0,
      tasa_exito: 100
    });

    // ESTADO PROYECTOS (PERMISOS / OBRAS)
    const permisosUsuarios = ref([]);
    const permisosObras = ref([]);
    const nuevoUsuarioProtegido = ref('');
    const nuevaObra = ref('');
    const terminalLiveContenido = ref('[Sistema preparado. Presione "Comenzar Depuración" para iniciar.]');
    const historialPermisosContenido = ref('');
    const ejecutandoDepuracion = ref(false);

    // ESTADO PROVEEDORES (COLA / SELECCIÓN / REGISTRO)
    const colaProveedores = ref([]);
    const proveedoresRegistrados = ref([]);
    const busquedaProveedores = ref('');
    const ejecutandoProveedores = ref(false);
    const terminalProveedoresContenido = ref('[Sistema preparado. Llena el formulario o agrega proveedores a la cola.]');

    // ESTADO CONTRATISTAS (DBA VS EN FILA + RPA ARYVE)
    const contratistasDB = ref([]);
    const cargandoContratistas = ref(false);
    const busquedaContratistas = ref('');
    const filtroEstatusContratistas = ref('TODOS');
    const colaContratistas = ref([]);
    const ejecutandoContratistas = ref(false);
    const terminalContratistasContenido = ref('[Sistema preparado. Marca los contratistas de la tabla izquierda para agregarlos a "EN FILA" y presiona "Iniciar Proceso".]');
    let intervaloContratistas = null;

    const formProveedor = ref({
      tipo_persona: 'MORAL',
      nombre: '',
      paterno: '',
      materno: '',
      rfc: '',
      calle: '',
      ext: '',
      cp: '',
      colonia: '',
      clave: 'EK-PROV-...',
      nombre_corto: '...'
    });

    // MODAL USUARIO
    const modalUsuarioAbierto = ref(false);
    const ejecutandoSelenium = ref(false);
    const estadoBot = ref(null);

    const formUsuario = ref({
      nombre: '',
      apellidos: '',
      correo: '',
      puesto: '',
      guardarEnProduccion: false
    });

    // CLASIFICADORES
    const modalClasificadorAbierto = ref(false);
    const puestoClasificadorSeleccionado = ref('');
    const puestoClasificadorTemporal = ref('');
    const infoClasificadorPuesto = ref({
      total: 0,
      area: '',
      categorias: [],
      clasificadores: {}
    });
    const infoClasificadorTemporal = ref({
      total: 0,
      area: '',
      categorias: [],
      clasificadores: {}
    });
    const estadoAsignacionClasificadores = ref({
      ejecutando: false,
      ok: null,
      mensaje: '',
      logs: []
    });
    let intervalAsignacionClasificadores = null;

    // MODAL POSICIÓN
    const modalPosicionAbierto = ref(false);
    const formPosicion = ref({
      nombre: '',
      area: '',
      niveles: [{ compania: '', nivel: '' }],
      grupos: [{ nombre: '' }],
      clasifs: [{ abuelo: '', padre: '', codigos: '' }]
    });

    // TORRE DE CONTROL: SALUD DE PROYECTOS (ESTADO GLOBAL FIJO)
    const sincronizandoOC = ref(false);
    const sincronizarOCAhora = async () => {
      sincronizandoOC.value = true;
      try {
        const res = await fetch('/api/torre/sync-oc', { method: 'POST' });
        if (res.ok) {
          await cargarProyectosTorre();
        }
      } catch (e) {
        console.error('Error forzando sync OC:', e);
      } finally {
        sincronizandoOC.value = false;
      }
    };

    const publicandoCliente = ref(false);
    const publicarVersionCliente = async () => {
      if (publicandoCliente.value) return;
      publicandoCliente.value = true;
      try {
        const res = await fetch('/api/torre/publicar-cliente', { method: 'POST' });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          alert('Error al publicar versión: ' + (data.mensaje || 'Error desconocido'));
        } else {
          await cargarProyectosTorre();
        }
      } catch (e) {
        console.error('Error publicando versión cliente:', e);
        alert('Fallo de conexión al publicar: ' + e.message);
      } finally {
        publicandoCliente.value = false;
      }
    };

    const proyectosTorre = ref([]);

    const cargarProyectosTorre = async () => {
      try {
        const res = await fetch('/api/torre/proyectos');
        if (res.ok) {
          const data = await res.json();
          proyectosTorre.value = Array.isArray(data) ? data : [];
        } else {
          proyectosTorre.value = [];
        }
      } catch (e) {
        proyectosTorre.value = [];
      }
    };

    const proveedoresFiltrados = computed(() => {
      const b = busquedaProveedores.value.trim().toUpperCase();
      if (!b) return proveedoresRegistrados.value;
      return proveedoresRegistrados.value.filter(p => 
        (p.id && String(p.id).toUpperCase().includes(b)) ||
        (p.clave && String(p.clave).toUpperCase().includes(b))
      );
    });

    const contratistasFiltrados = computed(() => {
      let list = contratistasDB.value;
      if (filtroEstatusContratistas.value === 'SIN_FOTO') {
        list = list.filter(c => !c.tiene_foto);
      } else if (filtroEstatusContratistas.value === 'COMPLETO') {
        list = list.filter(c => c.tiene_foto);
      }

      const q = busquedaContratistas.value.trim().toUpperCase();
      if (!q) return list;

      return list.filter(c => {
        const id = String(c.id || '').toUpperCase();
        const nom = (c.nombre || '').toUpperCase();
        const cve = String(c.clave || c.numpro || '').toUpperCase();
        const rfc = (c.rfc || '').toUpperCase();
        const rep = (c.representante || '').toUpperCase();
        return id.includes(q) || ('#' + id).includes(q) || nom.includes(q) || cve.includes(q) || rfc.includes(q) || rep.includes(q);
      });
    });

    
    const obrasFiltradas = computed(() => {
      const q = filtroBusquedaObra.value.trim().toUpperCase();
      if (!q) return obrasCatalogo.value;
      return obrasCatalogo.value.filter(o => {
        const cve = String(o.clave || '').toUpperCase();
        const nom = String(o.nombre || '').toUpperCase();
        const id = String(o.id_obra || '').toUpperCase();
        return cve.includes(q) || nom.includes(q) || id.includes(q);
      });
    });

    const arbolFiltrado = computed(() => {
      if (!arbolObraActual.value || !arbolObraActual.value.frentes) return [];
      const q = filtroArbolObra.value.trim().toUpperCase();
      if (!q) return arbolObraActual.value.frentes;

      const frentesFiltrados = [];
      for (const f of arbolObraActual.value.frentes) {
        const frenteMatch = (f.codigo && f.codigo.toUpperCase().includes(q)) || (f.nombre && f.nombre.toUpperCase().includes(q));
        const partidasFiltradas = [];

        for (const p of (f.partidas || [])) {
          const partidaMatch = (p.codigo && p.codigo.toUpperCase().includes(q)) || (p.nombre && p.nombre.toUpperCase().includes(q));
          const tarjetasFiltradas = (p.tarjetas || []).filter(t => 
            (t.codigo && t.codigo.toUpperCase().includes(q)) ||
            (t.clave_tarjeta && String(t.clave_tarjeta).toUpperCase().includes(q)) ||
            (t.nombre && t.nombre.toUpperCase().includes(q))
          );

          if (partidaMatch || tarjetasFiltradas.length > 0) {
            partidasFiltradas.push({
              ...p,
              tarjetas: (tarjetasFiltradas.length > 0 || !partidaMatch) ? tarjetasFiltradas : p.tarjetas
            });
          }
        }

        if (frenteMatch || partidasFiltradas.length > 0) {
          frentesFiltrados.push({
            ...f,
            partidas: (partidasFiltradas.length > 0 || !frenteMatch) ? partidasFiltradas : f.partidas
          });
        }
      }
      return frentesFiltrados;
    });

    // NAVEGACIÓN
    const cambiarVista = (vista) => {
      vistaActiva.value = vista;
      if (vista === 'PROYECTOS') {
        cargarPermisos();
      } else if (vista === 'PROVEEDORES') {
        cargarProveedores();
      } else if (vista === 'USUARIOS') {
        cargarUsuarios();
      } else if (vista === 'CONTRATISTAS') {
        cargarContratistas();
      } else if (vista === 'OBRAS') {
        cargarCatalogoObras();
      }
    };

    // MÉTODOS DE DATOS: USUARIOS
    const cargarMetricas = async (intentos = 3) => {
      try {
        const res = await fetch('/api/metricas');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        metricas.value = await res.json();
      } catch (e) {
        console.error('Error cargando métricas:', e);
        if (intentos > 1) setTimeout(() => cargarMetricas(intentos - 1), 1200);
      }
    };

    const cargarPuestos = async (intentos = 3) => {
      try {
        const res = await fetch('/api/usuarios/puestos');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        catalogoPuestos.value = Object.keys(data).sort();
      } catch (e) {
        console.error('Error cargando puestos:', e);
        if (intentos > 1) setTimeout(() => cargarPuestos(intentos - 1), 1200);
      }
    };

    const sincronizandoAryve = ref(false);

    const sincronizarUsuariosAryve = async () => {
      if (sincronizandoAryve.value) return;
      sincronizandoAryve.value = true;
      try {
        const res = await fetch('/api/usuarios/sincronizar-aryve', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Error al sincronizar con Aryve');
        await cargarUsuarios();
        await cargarMetricas();
      } catch (err) {
        console.error('Error sincronizando usuarios con Aryve:', err);
        alert(`Error al sincronizar con Aryve: ${err.message}`);
      } finally {
        sincronizandoAryve.value = false;
      }
    };

    const cargarUsuarios = async (intentos = 3) => {
      cargando.value = true;
      try {
        const q = encodeURIComponent(filtroBusqueda.value);
        const f = encodeURIComponent(filtroVigencia.value);
        const res = await fetch(`/api/usuarios/?q=${q}&filtro_vigencia=${f}&limit=200`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        usuarios.value = data.usuarios || [];

        if (usuarios.value.length && (!usuarioSeleccionado.value || !usuarios.value.some(u => u.id === usuarioSeleccionado.value.id))) {
          usuarioSeleccionado.value = usuarios.value[0];
          cargarClasificadoresUsuario(usuarios.value[0]);
        }
      } catch (e) {
        console.error('Error cargando usuarios:', e);
        if (intentos > 1) setTimeout(() => cargarUsuarios(intentos - 1), 1200);
      } finally {
        cargando.value = false;
      }
    };

    let searchTimeout = null;
    const alBuscar = () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        cargarUsuarios();
      }, 250);
    };

    const seleccionarUsuario = (u) => {
      usuarioSeleccionado.value = u;
      cargarClasificadoresUsuario(u);
    };

    // MÉTODOS: PROYECTOS (PERMISOS Y OBRAS)
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
        console.error(e);
      }
    };

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

    // MÉTODOS: PROVEEDORES (COLA / GENERACIÓN / SELENIUM)
    const cambiarTipoPersona = (tipo) => {
      formProveedor.value.tipo_persona = tipo;
      calcularClavesProveedor();
    };

    let calcTimeout = null;
    const calcularClavesProveedor = () => {
      clearTimeout(calcTimeout);
      calcTimeout = setTimeout(async () => {
        const nom = formProveedor.value.nombre.trim().toUpperCase();
        const tipo = formProveedor.value.tipo_persona;
        const pat = formProveedor.value.paterno ? formProveedor.value.paterno.trim().toUpperCase() : '';
        if (!nom) {
          formProveedor.value.clave = 'EK-PROV-...';
          formProveedor.value.nombre_corto = '...';
          return;
        }
        try {
          const res = await fetch('/api/operaciones/proveedores/calcular', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre: nom, tipo_persona: tipo, paterno: pat })
          });
          const data = await res.json();
          formProveedor.value.clave = data.clave;
          formProveedor.value.nombre_corto = data.nombre_corto;
        } catch (e) {
          console.error(e);
        }
      }, 120);
    };

    const cargarProveedores = async (intentos = 3) => {
      try {
        const [resCola, resReg] = await Promise.all([
          fetch('/api/operaciones/proveedores/cola'),
          fetch('/api/operaciones/proveedores/registrados')
        ]);
        if (resCola.ok) colaProveedores.value = await resCola.json();
        if (resReg.ok) proveedoresRegistrados.value = await resReg.json();
      } catch (e) {
        console.error('Error cargando proveedores:', e);
        if (intentos > 1) setTimeout(() => cargarProveedores(intentos - 1), 1200);
      }
    };

    const guardarEnListaProveedor = async () => {
      const nom = formProveedor.value.nombre.trim().toUpperCase();
      const rfc = formProveedor.value.rfc.trim().toUpperCase();
      if (!nom) {
        alert('El nombre o razón social es obligatorio.');
        return;
      }
      if (!rfc) {
        alert('El RFC es obligatorio.');
        return;
      }

      try {
        const res = await fetch('/api/operaciones/proveedores/cola', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tipo_persona: formProveedor.value.tipo_persona,
            nombre: nom,
            paterno: formProveedor.value.paterno ? formProveedor.value.paterno.trim().toUpperCase() : '',
            materno: formProveedor.value.materno ? formProveedor.value.materno.trim().toUpperCase() : '',
            rfc: rfc,
            calle: formProveedor.value.calle ? formProveedor.value.calle.trim().toUpperCase() : '',
            ext: formProveedor.value.ext ? formProveedor.value.ext.trim().toUpperCase() : '',
            colonia: formProveedor.value.colonia ? formProveedor.value.colonia.trim().toUpperCase() : '',
            cp: formProveedor.value.cp ? formProveedor.value.cp.trim().toUpperCase() : '',
            clave: formProveedor.value.clave,
            nombre_corto: formProveedor.value.nombre_corto
          })
        });
        colaProveedores.value = await res.json();

        // Limpiar formulario preservando el tipo de persona seleccionado
        const tipoActual = formProveedor.value.tipo_persona;
        formProveedor.value = {
          tipo_persona: tipoActual,
          nombre: '',
          paterno: '',
          materno: '',
          rfc: '',
          calle: '',
          ext: '',
          cp: '',
          colonia: '',
          clave: 'EK-PROV-...',
          nombre_corto: '...'
        };
      } catch (e) {
        console.error('Error agregando a la cola de proveedores:', e);
      }
    };

    const eliminarDeColaProveedor = async (idx) => {
      try {
        const res = await fetch(`/api/operaciones/proveedores/cola/${idx}`, { method: 'DELETE' });
        colaProveedores.value = await res.json();
      } catch (e) {
        console.error(e);
      }
    };

    const vaciarColaProveedor = async () => {
      if (!confirm('¿Deseas vaciar la lista de proveedores en espera?')) return;
      try {
        const res = await fetch('/api/operaciones/proveedores/cola', { method: 'DELETE' });
        colaProveedores.value = await res.json();
      } catch (e) {
        console.error(e);
      }
    };

    const iniciarProcesamientoProveedores = async () => {
      if (!colaProveedores.value.length) {
        alert('La lista de proveedores está vacía. Agrega al menos uno para iniciar.');
        return;
      }

      ejecutandoProveedores.value = true;
      terminalProveedoresContenido.value = `[Iniciando Selenium para procesar ${colaProveedores.value.length} proveedor(es) en Aryve...]\n`;

      try {
        const resInit = await fetch('/api/operaciones/proveedores/ejecutar', { method: 'POST' });
        const initData = await resInit.json();
        if (!resInit.ok) {
          terminalProveedoresContenido.value += `\n[ERROR]: ${initData.detail || 'Fallo al iniciar el bot.'}`;
          ejecutandoProveedores.value = false;
          return;
        }

        const interval = setInterval(async () => {
          const res = await fetch('/api/operaciones/proveedores/estado');
          const data = await res.json();
          if (data.logs && data.logs.length) {
            terminalProveedoresContenido.value = data.logs.join('\n');
            const el = document.getElementById('terminal-prov');
            if (el) el.scrollTop = el.scrollHeight;
          }
          if (!data.ejecutando) {
            clearInterval(interval);
            ejecutandoProveedores.value = false;
            await cargarProveedores();
          }
        }, 1000);
      } catch (e) {
        terminalProveedoresContenido.value += `\n[ERROR]: No se pudo conectar con el servidor.`;
        ejecutandoProveedores.value = false;
      }
    };

    const exportarCSVProveedores = () => {
      if (!proveedoresFiltrados.value.length) {
        alert('No hay proveedores registrados para exportar.');
        return;
      }
      let csv = 'id,clave\n';
      proveedoresFiltrados.value.forEach(p => {
        csv += `"${p.id}","${p.clave}"\n`;
      });
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'proveedores_id_clave.csv';
      a.click();
      URL.revokeObjectURL(url);
    };

    // =========================================================================
    // MÉTODOS CONTRATISTAS (DBA VS EN FILA + RPA ARYVE)
    // =========================================================================
    const cargarContratistas = async (forzar = false) => {
      if (cargandoContratistas.value) return; // Anti-collision guard
      cargandoContratistas.value = true;
      try {
        const [resDb, resCola] = await Promise.all([
          fetch(`/api/contratistas/db?forzar=${forzar}`),
          fetch('/api/contratistas/cola')
        ]);
        if (resDb.ok) contratistasDB.value = await resDb.json();
        if (resCola.ok) colaContratistas.value = await resCola.json();
      } catch (e) {
        console.error('Error cargando contratistas:', e);
      } finally {
        cargandoContratistas.value = false;
      }
    };

    const estaEnFila = (c) => {
      if (!c) return false;
      const cid = c.id !== undefined && c.id !== null ? String(c.id).trim() : null;
      const cve = String(c.clave || c.numpro || (typeof c === 'string' || typeof c === 'number' ? c : '')).trim();
      return colaContratistas.value.some(item => {
        const itemId = item.id !== undefined && item.id !== null ? String(item.id).trim() : null;
        const itemCve = String(item.clave || item.numpro || '').trim();
        if (cid && itemId && cid === itemId) return true;
        if (cve && itemCve && cve === itemCve) return true;
        return false;
      });
    };

    const toggleContratistaFila = async (item) => {
      try {
        const res = await fetch('/api/contratistas/cola/toggle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item)
        });
        if (res.ok) {
          colaContratistas.value = await res.json();
        }
      } catch (e) {
        console.error('Error toggle fila contratistas:', e);
      }
    };

    const quitarDeFila = async (itemOrKey) => {
      try {
        const key = typeof itemOrKey === 'object' ? (itemOrKey.clave || itemOrKey.numpro || itemOrKey.id) : itemOrKey;
        const res = await fetch(`/api/contratistas/cola/${key}`, { method: 'DELETE' });
        if (res.ok) {
          colaContratistas.value = await res.json();
        }
      } catch (e) {
        console.error('Error quitando de fila:', e);
      }
    };

    const vaciarFila = async () => {
      try {
        const res = await fetch('/api/contratistas/cola', { method: 'DELETE' });
        if (res.ok) {
          colaContratistas.value = [];
        }
      } catch (e) {
        console.error('Error vaciando fila:', e);
      }
    };

    const sincronizarContratistasDB = async () => {
      await cargarContratistas(true);
    };

    const seleccionarTodosSinFoto = async () => {
      const pendientes = contratistasFiltrados.value.filter(c => !c.tiene_foto);
      if (!pendientes.length) return;
      try {
        const res = await fetch('/api/contratistas/cola/sincronizar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ items: pendientes })
        });
        if (res.ok) {
          colaContratistas.value = await res.json();
        }
      } catch (e) {
        console.error('Error seleccionando contratistas sin foto:', e);
      }
    };
    const seleccionarTodosSinMapear = seleccionarTodosSinFoto;

    const limpiarTerminalContratistas = () => {
      terminalContratistasContenido.value = '[Consola limpia. Esperando inicio de tareas...]';
    };

    const iniciarProcesamientoContratistas = async () => {
      if (!colaContratistas.value.length) {
        alert('La lista "EN FILA" está vacía. Marca al menos un contratista de la tabla izquierda.');
        return;
      }
      ejecutandoContratistas.value = true;
      terminalContratistasContenido.value = `[Iniciando proceso para ${colaContratistas.value.length} contratista(s) en fila...]\n`;

      try {
        const resInit = await fetch('/api/contratistas/iniciar', { method: 'POST' });
        const initData = await resInit.json();
        if (!resInit.ok) {
          terminalContratistasContenido.value += `\n[ERROR]: ${initData.detail || initData.mensaje || 'Fallo al iniciar el bot.'}`;
          ejecutandoContratistas.value = false;
          return;
        }

        if (intervaloContratistas) clearInterval(intervaloContratistas);
        intervaloContratistas = setInterval(async () => {
          try {
            const res = await fetch('/api/contratistas/estado');
            const data = await res.json();
            if (data.logs && data.logs.length) {
              terminalContratistasContenido.value = data.logs.join('\n');
              const el = document.getElementById('terminal-contratistas');
              if (el) el.scrollTop = el.scrollHeight;
            }
            if (data.cola) {
              const prevLen = colaContratistas.value.length;
              colaContratistas.value = data.cola;
              if (data.cola.length !== prevLen) {
                // Se guardo un contratista en JSON, refrescar tabla para mostrarlo en verde en tiempo real
                cargarContratistas(false);
              }
            }
            if (!data.ejecutando) {
              clearInterval(intervaloContratistas);
              ejecutandoContratistas.value = false;
              await cargarContratistas(true);
            }
          } catch (err) {
            console.error('Error sondeando estado:', err);
          }
        }, 1000);
      } catch (e) {
        terminalContratistasContenido.value += `\n[ERROR]: No se pudo conectar con el servidor: ${e}`;
        ejecutandoContratistas.value = false;
      }
    };

    const detenerProcesamientoContratistas = async () => {
      try {
        const res = await fetch('/api/contratistas/detener', { method: 'POST' });
        const data = await res.json();
        terminalContratistasContenido.value += `\n[SOLICITUD]: ${data.mensaje}`;
      } catch (e) {
        console.error('Error deteniendo bot:', e);
      }
    };

    // MÉTODOS MODAL USUARIO
    const abrirModalUsuario = () => {
      estadoBot.value = null;
      ejecutandoSelenium.value = false;
      busquedaPuestoNuevoUsuario.value = formUsuario.value.puesto || '';
      mostrarDropdownPuestoNuevoUsuario.value = false;
      modalUsuarioAbierto.value = true;
    };

    const cerrarModalUsuario = () => {
      modalUsuarioAbierto.value = false;
    };

    const guardarDatosEnFicha = () => {
      if (!formUsuario.value.nombre || !formUsuario.value.apellidos || !formUsuario.value.correo) {
        estadoBot.value = { ok: false, msg: 'Completa Nombre, Apellidos y Correo/Clave.' };
        return;
      }
      estadoBot.value = { ok: true, msg: 'Datos confirmados en la ficha. Listo para iniciar Selenium.' };
    };

    const editarDatosEnFicha = () => {
      estadoBot.value = { ok: true, msg: 'Modo edición habilitado.' };
    };

    const limpiarFormularioUsuario = () => {
      formUsuario.value = {
        nombre: '',
        apellidos: '',
        correo: '',
        puesto: '',
        guardarEnProduccion: false
      };
      busquedaPuestoNuevoUsuario.value = '';
      mostrarDropdownPuestoNuevoUsuario.value = false;
      estadoBot.value = null;
    };

    let intervalCreacion = null;

    const iniciarPollingCreacion = () => {
      if (intervalCreacion) clearInterval(intervalCreacion);
      intervalCreacion = setInterval(async () => {
        try {
          const stRes = await fetch('/api/usuarios/crear/estado');
          const st = await stRes.json();
          
          if (st.mensaje) {
            estadoBot.value = { ok: st.ok, msg: st.mensaje };
          }

          if (!st.ejecutando) {
            clearInterval(intervalCreacion);
            intervalCreacion = null;
            ejecutandoSelenium.value = false;
            if (st.ok) {
              await cargarUsuarios();
              await cargarMetricas();
            }
          }
        } catch (err) {
          console.error('Error polling estado:', err);
        }
      }, 1200);
    };

    const iniciarCreacionSelenium = async () => {
      if (!formUsuario.value.nombre || !formUsuario.value.apellidos || !formUsuario.value.correo) {
        estadoBot.value = { ok: false, msg: 'Faltan campos obligatorios para iniciar el alta.' };
        return;
      }

      ejecutandoSelenium.value = true;
      estadoBot.value = { ok: null, msg: `Iniciando sesión en Aryve y preparando formulario...` };

      try {
        const res = await fetch('/api/usuarios/crear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: formUsuario.value.nombre,
            apellidos: formUsuario.value.apellidos,
            correo: formUsuario.value.correo,
            clave: formUsuario.value.correo,
            puesto: formUsuario.value.puesto,
            guardar_en_produccion: formUsuario.value.guardarEnProduccion
          })
        });

        const data = await res.json();
        if (!res.ok) {
          estadoBot.value = { ok: false, msg: data.detail || 'No se pudo iniciar el bot.' };
          ejecutandoSelenium.value = false;
          return;
        }

        iniciarPollingCreacion();
      } catch (e) {
        estadoBot.value = { ok: false, msg: 'Error de comunicación con el servidor.' };
        ejecutandoSelenium.value = false;
      }
    };

    const reiniciarCreacionSelenium = async () => {
      if (!formUsuario.value.nombre || !formUsuario.value.apellidos || !formUsuario.value.correo) {
        estadoBot.value = { ok: false, msg: 'Faltan campos obligatorios para reiniciar el alta.' };
        return;
      }

      if (intervalCreacion) {
        clearInterval(intervalCreacion);
        intervalCreacion = null;
      }

      ejecutandoSelenium.value = true;
      estadoBot.value = { ok: null, msg: 'Deteniendo Selenium, cerrando ventana y reiniciando...' };

      try {
        const res = await fetch('/api/usuarios/crear/reiniciar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: formUsuario.value.nombre,
            apellidos: formUsuario.value.apellidos,
            correo: formUsuario.value.correo,
            clave: formUsuario.value.correo,
            puesto: formUsuario.value.puesto,
            guardar_en_produccion: formUsuario.value.guardarEnProduccion
          })
        });

        const data = await res.json();
        if (!res.ok) {
          estadoBot.value = { ok: false, msg: data.detail || 'No se pudo reiniciar el bot.' };
          ejecutandoSelenium.value = false;
          return;
        }

        estadoBot.value = { ok: null, msg: 'Ventana reiniciada. Reconectando a Aryve...' };
        iniciarPollingCreacion();
      } catch (e) {
        estadoBot.value = { ok: false, msg: 'Error al solicitar reinicio de Selenium.' };
        ejecutandoSelenium.value = false;
      }
    };

    // MÉTODOS MODAL POSICIÓN
    const abrirModalPosicion = () => {
      modalPosicionAbierto.value = true;
    };

    const cerrarModalPosicion = () => {
      modalPosicionAbierto.value = false;
    };

    const agregarFilaNivel = () => formPosicion.value.niveles.push({ compania: '', nivel: '' });
    const quitarFilaNivel = () => {
      if (formPosicion.value.niveles.length > 1) formPosicion.value.niveles.pop();
    };

    const agregarFilaGrupo = () => formPosicion.value.grupos.push({ nombre: '' });
    const quitarFilaGrupo = () => {
      if (formPosicion.value.grupos.length > 1) formPosicion.value.grupos.pop();
    };

    const agregarFilaClasif = () => formPosicion.value.clasifs.push({ abuelo: '', padre: '', codigos: '' });
    const quitarFilaClasif = () => {
      if (formPosicion.value.clasifs.length > 1) formPosicion.value.clasifs.pop();
    };

    const guardarNuevaPosicion = async () => {
      if (!formPosicion.value.nombre.trim()) {
        alert('Ingrese el nombre de la posición.');
        return;
      }

      const niveles = formPosicion.value.niveles.filter(n => n.compania && n.nivel);
      const grupos = formPosicion.value.grupos.map(g => g.nombre.trim()).filter(Boolean);

      const clasificadores = {};
      formPosicion.value.clasifs.forEach(c => {
        if (c.padre && c.codigos) {
          const cods = c.codigos.split('\n').map(x => x.trim()).filter(Boolean);
          if (c.abuelo) {
            if (!clasificadores[c.abuelo]) clasificadores[c.abuelo] = {};
            clasificadores[c.abuelo][c.padre] = cods;
          } else {
            clasificadores[c.padre] = cods;
          }
        }
      });

      try {
        const res = await fetch('/api/usuarios/puestos', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nombre: formPosicion.value.nombre,
            area_organizacional: formPosicion.value.area,
            niveles: niveles,
            grupos: grupos,
            clasificadores: clasificadores
          })
        });

        const data = await res.json();
        if (res.ok) {
          alert(data.mensaje);
          await cargarPuestos();
          cerrarModalPosicion();
        } else {
          alert(data.detail || 'Error al guardar la posición.');
        }
      } catch (e) {
        alert('Error de conexión.');
      }
    };

    // ========================================================
    // MÉTODOS: CLASIFICADORES DE USUARIO (Aryve / puestos.json)
    // ========================================================
    const cargarInfoPuesto = async (puesto) => {
      if (!puesto) {
        return { total: 0, area: '', categorias: [], clasificadores: {} };
      }
      try {
        const res = await fetch(`/api/usuarios/clasificadores/puesto-info?puesto=${encodeURIComponent(puesto)}`);
        if (res.ok) {
          const d = await res.json();
          return {
            total: d.total_clasificadores || 0,
            area: d.area || '',
            categorias: d.categorias || [],
            clasificadores: d.clasificadores || {}
          };
        }
      } catch (e) {
        console.error('Error obteniendo info de clasificadores:', e);
      }
      return { total: 0, area: '', categorias: [], clasificadores: {} };
    };

    const cargarClasificadoresUsuario = async (u) => {
      if (!u) return;
      const puesto = (u.puesto && u.puesto !== 'No especificado') ? u.puesto : '';
      puestoClasificadorSeleccionado.value = puesto;
      if (puesto) {
        infoClasificadorPuesto.value = await cargarInfoPuesto(puesto);
      } else {
        infoClasificadorPuesto.value = { total: 0, area: '', categorias: [], clasificadores: {} };
      }
    };

    const abrirModalClasificador = async () => {
      puestoClasificadorTemporal.value = puestoClasificadorSeleccionado.value || (usuarioSeleccionado.value ? usuarioSeleccionado.value.puesto : '') || '';
      busquedaPuestoClasificador.value = puestoClasificadorTemporal.value || '';
      mostrarDropdownPuestoClasificador.value = false;
      if (puestoClasificadorTemporal.value) {
        infoClasificadorTemporal.value = await cargarInfoPuesto(puestoClasificadorTemporal.value);
      } else {
        infoClasificadorTemporal.value = { total: 0, area: '', categorias: [], clasificadores: {} };
      }
      modalClasificadorAbierto.value = true;
    };

    const cerrarModalClasificador = () => {
      modalClasificadorAbierto.value = false;
    };

    const alCambiarPuestoModalClasificador = async () => {
      if (puestoClasificadorTemporal.value) {
        infoClasificadorTemporal.value = await cargarInfoPuesto(puestoClasificadorTemporal.value);
      } else {
        infoClasificadorTemporal.value = { total: 0, area: '', categorias: [], clasificadores: {} };
      }
    };

    const confirmarSeleccionPuestoClasificador = () => {
      puestoClasificadorSeleccionado.value = puestoClasificadorTemporal.value;
      infoClasificadorPuesto.value = { ...infoClasificadorTemporal.value };
      modalClasificadorAbierto.value = false;
    };

    const borrarClasificadoresSeleccion = () => {
      puestoClasificadorSeleccionado.value = '';
      infoClasificadorPuesto.value = { total: 0, area: '', categorias: [], clasificadores: {} };
      estadoAsignacionClasificadores.value = {
        ejecutando: false,
        ok: null,
        mensaje: 'Selección de clasificadores limpiada. Usa "Actualizar" para elegir un puesto.',
        logs: []
      };
    };

    const pollingAsignacionClasificadores = () => {
      if (intervalAsignacionClasificadores) clearInterval(intervalAsignacionClasificadores);
      intervalAsignacionClasificadores = setInterval(async () => {
        try {
          const res = await fetch('/api/usuarios/clasificadores/estado');
          if (res.ok) {
            const data = await res.json();
            estadoAsignacionClasificadores.value.ejecutando = data.ejecutando;
            estadoAsignacionClasificadores.value.ok = data.ok;
            estadoAsignacionClasificadores.value.mensaje = data.mensaje;
            estadoAsignacionClasificadores.value.logs = data.logs || [];

            if (!data.ejecutando) {
              clearInterval(intervalAsignacionClasificadores);
              intervalAsignacionClasificadores = null;
            }
          }
        } catch (e) {
          console.error('Error polling clasificadores:', e);
        }
      }, 1200);
    };

    const iniciarAsignacionClasificadores = async () => {
      if (!usuarioSeleccionado.value || !usuarioSeleccionado.value.id) {
        alert('Debes seleccionar un usuario de la lista.');
        return;
      }
      const puestoAEnviar = puestoClasificadorTemporal.value || puestoClasificadorSeleccionado.value;
      if (!puestoAEnviar) {
        alert('Debes seleccionar un puesto usando el botón "Actualizar" antes de iniciar.');
        return;
      }

      puestoClasificadorSeleccionado.value = puestoAEnviar;

      if (modalClasificadorAbierto.value) {
        confirmarSeleccionPuestoClasificador();
      }

      estadoAsignacionClasificadores.value = {
        ejecutando: true,
        ok: null,
        mensaje: `Iniciando sesión en Aryve para usuario #${usuarioSeleccionado.value.id} (${puestoAEnviar})...`,
        logs: ['Iniciando automatización Selenium...']
      };

      try {
        const res = await fetch('/api/usuarios/clasificadores/iniciar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id_usuario: usuarioSeleccionado.value.id,
            puesto: puestoAEnviar,
            nombre_usuario: usuarioSeleccionado.value.nombre_completo || ''
          })
        });

        const data = await res.json();
        if (!res.ok) {
          estadoAsignacionClasificadores.value = {
            ejecutando: false,
            ok: false,
            mensaje: data.detail || 'Error al iniciar la asignación.',
            logs: [`[ERROR]: ${data.detail || 'Fallo al iniciar el bot.'}`]
          };
          return;
        }

        pollingAsignacionClasificadores();
      } catch (e) {
        estadoAsignacionClasificadores.value = {
          ejecutando: false,
          ok: false,
          mensaje: 'Error de conexión con el backend.',
          logs: ['[ERROR]: Error de conexión.']
        };
      }
    };

    
    // ==========================================
    // MÉTODOS OBRAS & WBS (OPTIMIZADOS O(1))
    // ==========================================
    const cargarCatalogoObras = async () => {
      cargandoObras.value = true;
      try {
        const [resCat, resMet] = await Promise.all([
          fetch('/api/obras/catalogo'),
          fetch('/api/obras/metricas')
        ]);
        if (resCat.ok) {
          obrasCatalogo.value = await resCat.json();
        }
        if (resMet.ok) {
          metricasObras.value = await resMet.json();
        }
        if (!obraSeleccionada.value && obrasCatalogo.value.length > 0) {
          const at1 = obrasCatalogo.value.find(o => String(o.clave).toUpperCase() === 'AT1');
          await seleccionarObra(at1 || obrasCatalogo.value[0]);
        }
      } catch (e) {
        console.error('Error cargando catálogo de obras:', e);
      } finally {
        cargandoObras.value = false;
      }
    };

    const seleccionarObra = async (obra) => {
      if (!obra) return;
      obraSeleccionada.value = obra;
      filtroArbolObra.value = '';

      const clave = String(obra.clave || obra.id_obra).toUpperCase();

      // Recuperación instantánea O(1) si está en caché cliente
      if (cacheArbolesObras.has(clave)) {
        arbolObraActual.value = cacheArbolesObras.get(clave);
        expandirFrenteInicial();
        return;
      }

      cargandoArbolObra.value = true;
      try {
        const res = await fetch(`/api/obras/${encodeURIComponent(clave)}/arbol`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        cacheArbolesObras.set(clave, data);
        arbolObraActual.value = data;
        expandirFrenteInicial();
      } catch (e) {
        console.error(`Error cargando árbol de obra ${clave}:`, e);
      } finally {
        cargandoArbolObra.value = false;
      }
    };

    const expandirFrenteInicial = () => {
      frentesExpandidos.value = {};
      partidasExpandidas.value = {};
      if (arbolObraActual.value && arbolObraActual.value.frentes && arbolObraActual.value.frentes.length > 0) {
        const f0 = arbolObraActual.value.frentes[0];
        frentesExpandidos.value[f0.codigo] = true;
        if (f0.partidas && f0.partidas.length > 0) {
          partidasExpandidas.value[f0.partidas[0].codigo] = true;
        }
        if (arbolObraActual.value.frentes.length > 1) {
          const f1 = arbolObraActual.value.frentes[1];
          frentesExpandidos.value[f1.codigo] = true;
          if (f1.partidas && f1.partidas.length > 0) {
            partidasExpandidas.value[f1.partidas[0].codigo] = true;
          }
        }
      }
    };

    const toggleFrente = (codigo) => {
      frentesExpandidos.value[codigo] = !frentesExpandidos.value[codigo];
    };

    const togglePartida = (codigo) => {
      partidasExpandidas.value[codigo] = !partidasExpandidas.value[codigo];
    };

    const expandirTodoArbol = () => {
      if (!arbolObraActual.value || !arbolObraActual.value.frentes) return;
      const fe = {};
      const pe = {};
      for (const f of arbolObraActual.value.frentes) {
        fe[f.codigo] = true;
        for (const p of (f.partidas || [])) {
          pe[p.codigo] = true;
        }
      }
      frentesExpandidos.value = fe;
      partidasExpandidas.value = pe;
    };

    const colapsarTodoArbol = () => {
      frentesExpandidos.value = {};
      partidasExpandidas.value = {};
    };

    const sincronizarObrasAryve = async () => {
      sincronizandoObras.value = true;
      try {
        const res = await fetch('/api/obras/sincronizar-aryve', { method: 'POST' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        await cargarCatalogoObras();
        if (obraSeleccionada.value) {
          await seleccionarObra(obraSeleccionada.value);
        }
      } catch (e) {
        console.error('Error sincronizando obras con Aryve:', e);
      } finally {
        sincronizandoObras.value = false;
      }
    };

    const recargarObras = async () => {
      cargandoObras.value = true;
      cacheArbolesObras.clear();
      try {
        await fetch('/api/obras/recargar', { method: 'POST' });
      } catch (e) {}
      await cargarCatalogoObras();
      if (obraSeleccionada.value) {
        await seleccionarObra(obraSeleccionada.value);
      }
      cargandoObras.value = false;
    };

    onMounted(() => {
      // 1. Carga escalonada (Waterfall) para evitar saturación de sockets concurrentes (cuellos de botella)
      cargarMetricas();
      setTimeout(cargarUsuarios, 70);
      setTimeout(cargarPuestos, 150);
      setTimeout(cargarProyectosTorre, 230);

      // Carga en diferido de vistas secundarias
      setTimeout(cargarPermisos, 350);
      setTimeout(cargarProveedores, 450);
      setTimeout(cargarContratistas, 550);
      setTimeout(cargarCatalogoObras, 650);

      // 2. Polling inteligente de Torre de Control: solo si la ventana está visible
      setInterval(() => {
        if (!document.hidden) {
          cargarProyectosTorre();
        }
      }, 6000);

      // 3. Polling inteligente de Contratistas:
      // Se ejecuta ÚNICAMENTE si la pestaña CONTRATISTAS está activa, visible y sin procesos corriendo
      setInterval(() => {
        if (!document.hidden && vistaActiva.value === 'CONTRATISTAS' && !ejecutandoContratistas.value && !cargandoContratistas.value) {
          cargarContratistas(false);
        }
      }, 15000);

      // 4. Page Visibility API: pausa llamadas cuando el usuario minimiza o cambia de ventana
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
          if (vistaActiva.value === 'CONTRATISTAS' && !cargandoContratistas.value) {
            cargarContratistas(false);
          } else if (vistaActiva.value === 'USUARIOS') {
            cargarUsuarios();
          }
          cargarProyectosTorre();
        }
      });
    });

    return {
      // Módulo Obras
      metricasObras,
      obrasCatalogo,
      cargandoObras,
      cargandoArbolObra,
      filtroBusquedaObra,
      obraSeleccionada,
      arbolObraActual,
      filtroArbolObra,
      frentesExpandidos,
      partidasExpandidas,
      obrasFiltradas,
      arbolFiltrado,
      cargarCatalogoObras,
      seleccionarObra,
      toggleFrente,
      togglePartida,
      expandirTodoArbol,
      colapsarTodoArbol,
      recargarObras,
      sincronizandoObras,
      sincronizarObrasAryve,

      // Torre de Control (Proyectos)
      proyectosTorre,
      sincronizandoOC,
      sincronizarOCAhora,
      publicandoCliente,
      publicarVersionCliente,
      cargarProyectosTorre,
      // Navegación
      vistaActiva,
      cambiarVista,
      cargando,
      usuarios,
      usuarioSeleccionado,
      filtroBusqueda,
      filtroVigencia,
      catalogoPuestos,
      metricas,
      alBuscar,
      cargarUsuarios,
      sincronizandoAryve,
      sincronizarUsuariosAryve,
      seleccionarUsuario,
      // Proyectos
      permisosUsuarios,
      permisosObras,
      nuevoUsuarioProtegido,
      nuevaObra,
      terminalLiveContenido,
      historialPermisosContenido,
      ejecutandoDepuracion,
      cargarPermisos,
      agregarUsuarioProtegido,
      eliminarUsuarioProtegido,
      agregarObra,
      eliminarObra,
      cargarObrasDesdeJSON,
      iniciarDepuracionPermisos,
      // Proveedores
      colaProveedores,
      proveedoresRegistrados,
      proveedoresFiltrados,
      busquedaProveedores,
      ejecutandoProveedores,
      terminalProveedoresContenido,
      formProveedor,
      cambiarTipoPersona,
      calcularClavesProveedor,
      cargarProveedores,
      guardarEnListaProveedor,
      eliminarDeColaProveedor,
      vaciarColaProveedor,
      iniciarProcesamientoProveedores,
      exportarCSVProveedores,
      // Contratistas
      contratistasDB,
      cargandoContratistas,
      busquedaContratistas,
      filtroEstatusContratistas,
      contratistasFiltrados,
      colaContratistas,
      ejecutandoContratistas,
      terminalContratistasContenido,
      cargarContratistas,
      estaEnFila,
      toggleContratistaFila,
      quitarDeFila,
      vaciarFila,
      sincronizarContratistasDB,
      seleccionarTodosSinMapear,
      limpiarTerminalContratistas,
      iniciarProcesamientoContratistas,
      detenerProcesamientoContratistas,
      // Buscadores reactivos de Puestos / Posiciones
      busquedaPuestoNuevoUsuario,
      mostrarDropdownPuestoNuevoUsuario,
      puestosFiltradosNuevoUsuario,
      seleccionarPuestoNuevoUsuario,
      limpiarPuestoNuevoUsuario,
      busquedaPuestoClasificador,
      mostrarDropdownPuestoClasificador,
      puestosFiltradosClasificador,
      seleccionarPuestoModalClasificador,
      limpiarPuestoModalClasificador,
      // Modal Usuario
      modalUsuarioAbierto,
      formUsuario,
      ejecutandoSelenium,
      estadoBot,
      abrirModalUsuario,
      cerrarModalUsuario,
      guardarDatosEnFicha,
      editarDatosEnFicha,
      limpiarFormularioUsuario,
      iniciarCreacionSelenium,
      reiniciarCreacionSelenium,
      // Modal Posición
      modalPosicionAbierto,
      formPosicion,
      abrirModalPosicion,
      cerrarModalPosicion,
      agregarFilaNivel,
      quitarFilaNivel,
      agregarFilaGrupo,
      quitarFilaGrupo,
      agregarFilaClasif,
      quitarFilaClasif,
      guardarNuevaPosicion,
      // Clasificadores
      modalClasificadorAbierto,
      puestoClasificadorSeleccionado,
      puestoClasificadorTemporal,
      infoClasificadorPuesto,
      infoClasificadorTemporal,
      estadoAsignacionClasificadores,
      cargarClasificadoresUsuario,
      abrirModalClasificador,
      cerrarModalClasificador,
      alCambiarPuestoModalClasificador,
      confirmarSeleccionPuestoClasificador,
      borrarClasificadoresSeleccion,
      iniciarAsignacionClasificadores
    };
  }
}).mount('#app');
