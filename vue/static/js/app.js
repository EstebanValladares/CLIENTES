const { createApp, ref, computed, onMounted } = Vue;

createApp({
  setup() {
    // ==========================================
    // SISTEMA DE TEMA CLARO / OSCURO (PERSISTENTE)
    // ==========================================
    const temaActual = ref(localStorage.getItem('theme_preference') === 'claro' ? 'claro' : 'oscuro');

    const aplicarTema = (modo) => {
      temaActual.value = modo;
      try {
        localStorage.setItem('theme_preference', modo);
      } catch (e) {}

      if (modo === 'claro') {
        document.documentElement.classList.add('theme-light');
        if (document.body) document.body.classList.add('theme-light');
      } else {
        document.documentElement.classList.remove('theme-light');
        if (document.body) document.body.classList.remove('theme-light');
      }
    };

    const toggleTema = () => {
      const nuevo = temaActual.value === 'claro' ? 'oscuro' : 'claro';
      aplicarTema(nuevo);
    };

    aplicarTema(temaActual.value);
    window.toggleTema = toggleTema;
    window.aplicarTema = aplicarTema;

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

    // Motor Insumos & Órdenes de Compra (Clon REA)
    const filtroInsumoClave = ref('');
    const filtroInsumoNombre = ref('');
    const filtroFolioOC = ref('');
    const modoBusquedaFolioOC = ref(false);
    const busquedaFolioEjecutada = ref(false);
    const ordenesCompraPorFolio = ref([]);
    const errorBusquedaFolioOC = ref('');
    const reporteInsumos = ref(null);
    const cargandoReporteInsumos = ref(false);
    const suministrandoObra = ref(false);
    const esMaster = ref(false);
        const modalMovimientosVisible = ref(false);
    const cargandoMovimientos = ref(false);
    const tabMovimientos = ref('OC');
    const movimientosActuales = ref({ requisiciones: [], ordenes_compra: [] });
    const insumoMovimientoSeleccionado = ref(null);

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

    // ==========================================
    // MÓDULO UNIFICADO: PROVEEDORES & CONTRATISTAS (EK10 / ARYVE)
    // ==========================================
    const provContraRegistros = ref([]);
    const provContraMetricas = ref({});
    const provContraCargando = ref(false);
    const provContraEjecutando = ref(false);
    const provContraModoReal = ref(false);
    const provContraLector = ref('db');
    const provContraInputNumpro = ref('');
    const provContraConsultandoDb = ref(false);
    const provContraSubiendoImagen = ref(false);
    const provContraBusqueda = ref('');
    const provContraFiltro = ref('TODOS');
    const provContraSeleccionados = ref([]);
    const provContraColumnaOrden = ref('proveedor');
    const provContraOrdenAsc = ref(true);
    const provContraTerminalLogs = ref('[Sistema preparado. Ingrese un número de proveedor o arrastre una captura EK9.]');
    const provContraModalEditor = ref(false);
    const provContraRegistroEditando = ref(null);
    const provContraModalVisor = ref(false);
    const provContraImagenVisorUrl = ref('');
    let provContraIntervaloTrabajo = null;


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

    // CREACION DE POSICIONES (AUTO-INCREMENTAL POS-XXXX & BOTON DE CALCULO)
    const metaPosiciones = ref({
      ultima_clave: 'POS-1077',
      siguiente_clave: 'POS-1078',
      puestos: [],
      categorias: []
    });
    const formCreacionPosicion = ref({
      clave: 'POS-1078',
      nombre: '',
      categoria: '',
      padre: '',
      estatus: 'Activo'
    });
    const guardandoPosicionSimple = ref(false);
    const resultadoCreacionPosicion = ref(null);
    const calculandoClave = ref(false);

    // Dropdowns reactivos sutiles y ligeros (sin datalist tosco a pantalla completa)
    const dropdownNombreAbierto = ref(false);
    const filtroNombre = computed(() => {
      const q = (formCreacionPosicion.value.nombre || '').trim().toLowerCase();
      const lista = metaPosiciones.value.puestos && metaPosiciones.value.puestos.length 
        ? metaPosiciones.value.puestos 
        : (catalogoPuestos.value || []);
      if (!q) return lista.slice(0, 30);
      return lista.filter(p => String(p).toLowerCase().includes(q)).slice(0, 30);
    });
    const seleccionarNombrePosicion = (p) => {
      formCreacionPosicion.value.nombre = p;
      dropdownNombreAbierto.value = false;
      if (catalogoPuestosDetalle.value && catalogoPuestosDetalle.value[p]) {
        const info = catalogoPuestosDetalle.value[p];
        if (!formCreacionPosicion.value.categoria && info.categoria) {
          formCreacionPosicion.value.categoria = info.categoria;
        }
        if (!formCreacionPosicion.value.padre && info.puesto_origen) {
          formCreacionPosicion.value.padre = info.puesto_origen;
        }
      }
    };

    const dropdownCategoriaAbierto = ref(false);
    const filtroCategoria = computed(() => {
      const q = (formCreacionPosicion.value.categoria || '').trim().toLowerCase();
      const lista = metaPosiciones.value.categorias && metaPosiciones.value.categorias.length 
        ? metaPosiciones.value.categorias 
        : [];
      if (!q) return lista.slice(0, 25);
      return lista.filter(c => String(c).toLowerCase().includes(q)).slice(0, 25);
    });
    const seleccionarCategoriaPosicion = (c) => {
      formCreacionPosicion.value.categoria = c;
      dropdownCategoriaAbierto.value = false;
    };

    const cargarMetaPosiciones = async () => {
      try {
        const res = await fetch('/api/usuarios/posiciones/meta');
        if (res.ok) {
          const data = await res.json();
          metaPosiciones.value = data;
          if (!formCreacionPosicion.value.clave || formCreacionPosicion.value.clave === 'POS-1052' || formCreacionPosicion.value.clave === 'POS-1067') {
            formCreacionPosicion.value.clave = data.siguiente_clave || 'POS-1078';
          }
        }
      } catch (e) {
        console.error('Error cargando meta posiciones:', e);
      }
    };

    const calcularSiguienteClave = async () => {
      calculandoClave.value = true;
      try {
        const res = await fetch('/api/usuarios/posiciones/meta');
        if (res.ok) {
          const data = await res.json();
          metaPosiciones.value = data;
          formCreacionPosicion.value.clave = data.siguiente_clave || 'POS-1078';
        } else {
          let num = 1077;
          const m = formCreacionPosicion.value.clave.match(/POS-(\d+)/);
          if (m) num = Math.max(num, parseInt(m[1], 10));
          formCreacionPosicion.value.clave = `POS-${String(num + 1).padStart(4, '0')}`;
        }
      } catch (e) {
        console.error('Error al calcular siguiente clave:', e);
      } finally {
        setTimeout(() => { calculandoClave.value = false; }, 350);
      }
    };

    const guardarPosicionSimple = async () => {
      const nom = formCreacionPosicion.value.nombre.trim();
      if (!nom) {
        alert('Por favor escribe o selecciona el NOMBRE de la posición.');
        return;
      }
      guardandoPosicionSimple.value = true;
      resultadoCreacionPosicion.value = null;
      try {
        const res = await fetch('/api/usuarios/posiciones/crear-simple', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formCreacionPosicion.value)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Error al guardar');
        resultadoCreacionPosicion.value = { ok: true, mensaje: data.mensaje };
        if (data.meta) {
          metaPosiciones.value = data.meta;
          formCreacionPosicion.value.clave = data.meta.siguiente_clave;
        }
        formCreacionPosicion.value.nombre = '';
        formCreacionPosicion.value.padre = '';
        await cargarPuestos();
        await cargarMetaPosiciones();
      } catch (e) {
        resultadoCreacionPosicion.value = { ok: false, error: e.message };
      } finally {
        guardandoPosicionSimple.value = false;
      }
    };

    const limpiarFormPosicionSimple = () => {
      formCreacionPosicion.value = {
        clave: metaPosiciones.value.siguiente_clave || 'POS-1078',
        nombre: '',
        categoria: '',
        padre: '',
        estatus: 'Activo'
      };
      resultadoCreacionPosicion.value = null;
      dropdownNombreAbierto.value = false;
      dropdownCategoriaAbierto.value = false;
    };

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

    // ==========================================
    // SISTEMA DE ACTUALIZACIÓN CLIENTES (EQUIPO)
    // ==========================================
    const actualizacionDisponibleCliente = ref(false);
    const actualizandoSistema = ref(false);

    const verificarActualizacionCliente = async () => {
      if (esMaster.value) return;
      try {
        const res = await fetch('/api/sistema/verificar-actualizacion');
        if (res.ok) {
          const data = await res.json();
          actualizacionDisponibleCliente.value = !!data.hay_actualizacion;
        }
      } catch (e) {}
    };

    const ejecutarActualizacionCliente = async () => {
      if (actualizandoSistema.value) return;
      if (!confirm('¿Deseas descargar la última versión del Dashboard publicada por la Torre? La página se recargará automáticamente al terminar.')) {
        return;
      }
      actualizandoSistema.value = true;
      try {
        const res = await fetch('/api/sistema/actualizar', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.ok) {
          alert('✅ ' + (data.mensaje || '¡Dashboard actualizado con éxito!'));
          window.location.reload();
        } else {
          alert('⚠️ Aviso: ' + (data.mensaje || 'No se pudo completar la actualización.'));
        }
      } catch (e) {
        alert('Error de conexión al actualizar: ' + e.message);
      } finally {
        actualizandoSistema.value = false;
      }
    };

    const cargarEntorno = async () => {
      try {
        const res = await fetch('/api/entorno');
        if (res.ok) {
          const data = await res.json();
          esMaster.value = !!data.es_master;
          if (!esMaster.value) {
            verificarActualizacionCliente();
            // Polling periódico para detectar nuevas versiones en clientes cada 45 segundos
            setInterval(verificarActualizacionCliente, 45000);
          }
        }
      } catch (e) {
        esMaster.value = false;
      }
    };
    cargarEntorno();

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

    
    
    const provContraEnRevision = computed(() => {
      return provContraRegistros.value.filter(r => !r.en_historial);
    });

    const provContraEnRevisionCount = computed(() => {
      return provContraEnRevision.value.length;
    });

    const provContraMarcadosProveedorCount = computed(() => {
      return provContraRegistros.value.filter(r => r.en_historial && r.quiere_proveedor && !r.id_ek10).length;
    });

    const provContraMarcadosContratistaCount = computed(() => {
      return provContraRegistros.value.filter(r => r.en_historial && r.quiere_contratista && !r.id_contratista).length;
    });

    const toggleOrdenProvContra = (col) => {
      if (provContraColumnaOrden.value === col) {
        provContraOrdenAsc.value = !provContraOrdenAsc.value;
      } else {
        provContraColumnaOrden.value = col;
        provContraOrdenAsc.value = true;
      }
    };

    const provContraFiltrados = computed(() => {
      let list = provContraRegistros.value.filter(r => r.en_historial);
      if (provContraFiltro.value === 'PENDIENTES') {
        list = list.filter(r => (!r.id_ek10 && r.quiere_proveedor) || (!r.id_contratista && r.quiere_contratista));
      } else if (provContraFiltro.value === 'MARCADOS') {
        list = list.filter(r => (r.quiere_proveedor && !r.id_ek10) || (r.quiere_contratista && !r.id_contratista));
      } else if (provContraFiltro.value === 'REGISTRADOS') {
        list = list.filter(r => Boolean(r.id_ek10 || r.id_contratista));
      }

      const q = provContraBusqueda.value.trim().toUpperCase();
      if (q) {
        list = list.filter(r => {
          const nom = (r.nombre || '').toUpperCase();
          const rfc = (r.rfc || '').toUpperCase();
          const num = String(r.proveedor || r.id || '').toUpperCase();
          const cve = (r.clave_proveedor || '').toUpperCase();
          const idek = String(r.id_ek10 || '').toUpperCase();
          const idct = String(r.id_contratista || '').toUpperCase();
          return nom.includes(q) || rfc.includes(q) || num.includes(q) || cve.includes(q) || idek.includes(q) || idct.includes(q);
        });
      }

      const col = provContraColumnaOrden.value;
      const asc = provContraOrdenAsc.value ? 1 : -1;
      return [...list].sort((a, b) => {
        let valA = a[col] ?? '';
        let valB = b[col] ?? '';
        if (col === 'proveedor') {
          return ((Number(valA) || 0) - (Number(valB) || 0)) * asc;
        }
        return String(valA).localeCompare(String(valB)) * asc;
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
      } else if (vista === 'PROV_CONTRA') {
        cargarProvContraRegistros();
      } else if (vista === 'USUARIOS') {
        cargarUsuarios();
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
        cargarMetaPosiciones();

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

    
    // ==========================================
    // MÉTODOS: PROVEEDORES & CONTRATISTAS UNIFICADO
    // ==========================================
    const cargarProvContraRegistros = async () => {
      provContraCargando.value = true;
      try {
        const res = await fetch('/api/prov-contra/registros');
        if (res.ok) {
          const data = await res.json();
          provContraRegistros.value = data.registros || [];
          provContraMetricas.value = data.metricas || {};
        }
      } catch (e) {
        console.error('Error cargando registros de proveedores/contratistas:', e);
      } finally {
        provContraCargando.value = false;
      }
    };

    const consultarProvContraPorNumpro = async () => {
      const numeros = [...new Set((provContraInputNumpro.value.match(/\d+/g) || []))];
      if (!numeros.length) {
        alert('Escriba el número de proveedor (ej. 11569 o varios: 11569, 11570).');
        return;
      }
      provContraConsultandoDb.value = true;
      provContraInputNumpro.value = '';
      try {
        for (const num of numeros) {
          const res = await fetch('/api/prov-contra/consultar-db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ numpro: num })
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            provContraTerminalLogs.value += `\n[OK]: Proveedor #${num} consultado desde Enkontrol.`;
          } else {
            provContraTerminalLogs.value += `\n[AVISO]: Proveedor #${num} no encontrado o error: ${data.detail || 'Error'}`;
          }
        }
        await cargarProvContraRegistros();
      } catch (e) {
        alert('Error de conexión con el servidor al consultar Enkontrol: ' + e.message);
      } finally {
        provContraConsultandoDb.value = false;
      }
    };

    const manejarDropCapturaProvContra = async (e) => {
      const files = [...(e.dataTransfer.files || [])];
      for (const file of files) {
        await subirArchivoCapturaProvContra(file);
      }
    };

    const manejarSeleccionCapturaProvContra = async (e) => {
      const files = [...(e.target.files || [])];
      for (const file of files) {
        await subirArchivoCapturaProvContra(file);
      }
      e.target.value = '';
    };

    const verificarRegistroProvContra = async (r) => {
      if (!confirm(`¿Verificar en EK10 el proveedor ${r.proveedor} ${r.nombre}?\nSe busca su RFC; si ya existe se anota su ID EK10. No se crea nada.`)) return;
      provContraEjecutando.value = true;
      try {
        const res = await fetch('/api/prov-contra/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ verificar: [r.id], proveedor: [], contratista: [], guardar: false })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          alert('Error: ' + (data.detail || data.mensaje || 'Error al verificar'));
          provContraEjecutando.value = false;
          return;
        }
        provContraTerminalLogs.value = `[${new Date().toLocaleTimeString()}] Verificando proveedor #${r.proveedor} en EK10...`;
        if (provContraIntervaloTrabajo) clearInterval(provContraIntervaloTrabajo);
        provContraIntervaloTrabajo = setInterval(async () => {
          try {
            const resp = await fetch('/api/prov-contra/trabajo');
            if (resp.ok) {
              const est = await resp.json();
              provContraTerminalLogs.value = est.lineas.join('\n');
              const el = document.getElementById('terminal-prov-contra');
              if (el) el.scrollTop = el.scrollHeight;
              if (!est.activo) {
                clearInterval(provContraIntervaloTrabajo);
                provContraEjecutando.value = false;
                await cargarProvContraRegistros();
              }
            }
          } catch (e) {
            console.error('Error obteniendo estado del trabajo:', e);
          }
        }, 1200);
      } catch (e) {
        alert('Fallo de conexión al verificar: ' + e.message);
        provContraEjecutando.value = false;
      }
    };

    const ejecutarMarcadosProvContra = async () => {
      const provs = provContraRegistros.value.filter(r => r.en_historial && r.quiere_proveedor && !r.id_ek10).map(r => r.id);
      const contras = provContraRegistros.value.filter(r => r.en_historial && r.quiere_contratista && !r.id_contratista).map(r => r.id);
      if (!provs.length && !contras.length) {
        alert('No hay registros marcados en el historial. Asegúrese de marcar la casilla "Generar" de Proveedor o Contratista.');
        return;
      }
      const esReal = provContraModoReal.value;
      const texto = `${esReal ? '⚡ ALTA REAL' : '🔍 PRUEBA (no guarda)'}\n${provs.length} proveedor(es) y ${contras.length} contratista(s).\n¿Continuar con la ejecución?`;
      if (!confirm(texto)) return;

      provContraEjecutando.value = true;
      try {
        const res = await fetch('/api/prov-contra/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proveedor: provs, contratista: contras, guardar: esReal })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          alert('Error: ' + (data.detail || data.mensaje || 'Error al iniciar'));
          provContraEjecutando.value = false;
          return;
        }
        provContraTerminalLogs.value = `[${new Date().toLocaleTimeString()}] Iniciando ejecución (${esReal ? 'REAL' : 'PRUEBA'})...`;
        if (provContraIntervaloTrabajo) clearInterval(provContraIntervaloTrabajo);
        provContraIntervaloTrabajo = setInterval(async () => {
          try {
            const resp = await fetch('/api/prov-contra/trabajo');
            if (resp.ok) {
              const est = await resp.json();
              provContraTerminalLogs.value = est.lineas.join('\n');
              const el = document.getElementById('terminal-prov-contra');
              if (el) el.scrollTop = el.scrollHeight;
              if (!est.activo) {
                clearInterval(provContraIntervaloTrabajo);
                provContraEjecutando.value = false;
                await cargarProvContraRegistros();
              }
            }
          } catch (e) {
            console.error('Error obteniendo estado del trabajo:', e);
          }
        }, 1200);
      } catch (e) {
        alert('Fallo de conexión al ejecutar: ' + e.message);
        provContraEjecutando.value = false;
      }
    };

    const subirArchivoCapturaProvContra = (file) => {
      provContraSubiendoImagen.value = true;
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const res = await fetch('/api/prov-contra/subir-captura', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              imagen_base64: reader.result,
              filename: file.name,
              lector: provContraLector.value
            })
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            await cargarProvContraRegistros();
            provContraTerminalLogs.value += `\n[OK]: Captura ${file.name} procesada correctamente.`;
          } else {
            alert(data.detail || 'Error procesando la captura de imagen.');
          }
        } catch (err) {
          alert('Fallo de conexión al enviar captura al servidor.');
        } finally {
          provContraSubiendoImagen.value = false;
        }
      };
      reader.readAsDataURL(file);
    };

    const toggleCasillaRegistro = async (id, campo, valor) => {
      try {
        await fetch(`/api/prov-contra/registros/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ [campo]: valor })
        });
        const item = provContraRegistros.value.find(r => r.id === id);
        if (item) item[campo] = valor ? 1 : 0;
      } catch (e) {
        console.error('Error actualizando casilla:', e);
      }
    };

    const enviarRegistroAHistorial = async (id) => {
      try {
        const res = await fetch(`/api/prov-contra/registros/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ en_historial: 1 })
        });
        if (res.ok) {
          await cargarProvContraRegistros();
        }
      } catch (e) {
        console.error('Error enviando a historial:', e);
      }
    };

    const enviarTodosAHistorial = async () => {
      const pendientes = provContraEnRevision.value;
      for (const item of pendientes) {
        await enviarRegistroAHistorial(item.id);
      }
      await cargarProvContraRegistros();
    };

    const toggleSeleccionProvContra = (id) => {
      const idx = provContraSeleccionados.value.indexOf(id);
      if (idx > -1) {
        provContraSeleccionados.value.splice(idx, 1);
      } else {
        provContraSeleccionados.value.push(id);
      }
    };

    const toggleSeleccionarTodosProvContra = () => {
      if (provContraSeleccionados.value.length === provContraFiltrados.value.length) {
        provContraSeleccionados.value = [];
      } else {
        provContraSeleccionados.value = provContraFiltrados.value.map(r => r.id);
      }
    };

    const abrirEditorProvContra = async (item) => {
      try {
        const res = await fetch(`/api/prov-contra/registros/${item.id}`);
        if (res.ok) {
          provContraRegistroEditando.value = await res.json();
          provContraModalEditor.value = true;
        }
      } catch (e) {
        console.error('Error abriendo editor:', e);
      }
    };

    const guardarEdicionProvContra = async () => {
      if (!provContraRegistroEditando.value) return;
      try {
        const id = provContraRegistroEditando.value.id;
        const res = await fetch(`/api/prov-contra/registros/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ campos: provContraRegistroEditando.value.campos })
        });
        if (res.ok) {
          provContraModalEditor.value = false;
          await cargarProvContraRegistros();
        } else {
          const err = await res.json();
          alert(err.detail || 'Error guardando campos editados.');
        }
      } catch (e) {
        alert('Error conectando con el servidor al guardar.');
      }
    };

    const eliminarRegistroProvContra = async (id) => {
      if (!confirm('¿Deseas eliminar este registro del historial?')) return;
      try {
        const res = await fetch(`/api/prov-contra/registros/${id}`, { method: 'DELETE' });
        if (res.ok) {
          provContraSeleccionados.value = provContraSeleccionados.value.filter(i => i !== id);
          await cargarProvContraRegistros();
        }
      } catch (e) {
        console.error('Error eliminando registro:', e);
      }
    };

    const abrirVisorImagenProvContra = (id) => {
      provContraImagenVisorUrl.value = `/api/prov-contra/imagen/${id}`;
      provContraModalVisor.value = true;
    };

    const iniciarEjecucionProvContra = async (soloVerificar = false) => {
      if (provContraSeleccionados.value.length === 0) {
        alert('Seleccione al menos un registro de la tabla para procesar.');
        return;
      }

      provContraEjecutando.value = true;
      provContraTerminalLogs.value = `[Iniciando Selenium para procesar ${provContraSeleccionados.value.length} registro(s)...]`;

      try {
        const payload = {
          proveedor: soloVerificar ? [] : provContraSeleccionados.value,
          contratista: soloVerificar ? [] : provContraSeleccionados.value,
          guardar: provContraModoReal.value,
          verificar: soloVerificar ? provContraSeleccionados.value : []
        };

        const res = await fetch('/api/prov-contra/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json();
          provContraTerminalLogs.value += `\n[ERROR]: ${err.detail || 'Fallo iniciando automatización.'}`;
          provContraEjecutando.value = false;
          return;
        }

        // Iniciar Polling de logs
        if (provContraIntervaloTrabajo) clearInterval(provContraIntervaloTrabajo);
        provContraIntervaloTrabajo = setInterval(async () => {
          try {
            const resp = await fetch('/api/prov-contra/trabajo');
            if (resp.ok) {
              const est = await resp.json();
              provContraTerminalLogs.value = est.lineas.join('\n');
              const el = document.getElementById('terminal-prov-contra');
              if (el) el.scrollTop = el.scrollHeight;

              if (!est.activo) {
                clearInterval(provContraIntervaloTrabajo);
                provContraEjecutando.value = false;
                await cargarProvContraRegistros();
              }
            }
          } catch (e) {
            console.error('Error obteniendo estado del trabajo:', e);
          }
        }, 1200);

      } catch (e) {
        provContraTerminalLogs.value += `\n[ERROR]: Fallo de conexión: ${e.message}`;
        provContraEjecutando.value = false;
      }
    };

    const limpiarTerminalProvContra = async () => {
      try {
        await fetch('/api/prov-contra/limpiar-terminal', { method: 'POST' });
        provContraTerminalLogs.value = '[Consola limpia. Sistema listo.]';
      } catch (e) {
        provContraTerminalLogs.value = '[Consola limpia.]';
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
        await cargarMetaPosiciones();
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
        const res = await fetch('/api/usuarios/clasificadores/puesto-info?puesto=' + encodeURIComponent(puesto));
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

    const cargarReporteInsumos = async (forzar = false) => {
      if (!obraSeleccionada.value) return;
      const clave = String(obraSeleccionada.value.clave || obraSeleccionada.value.id_obra).toUpperCase();
      modoBusquedaFolioOC.value = false;
      busquedaFolioEjecutada.value = false;
      ordenesCompraPorFolio.value = [];
      errorBusquedaFolioOC.value = '';
      cargandoReporteInsumos.value = true;
      try {
        const params = new URLSearchParams({
          obra: clave,
          insumo: filtroInsumoClave.value.trim(),
          nombre: filtroInsumoNombre.value.trim(),
          forzar: forzar ? 'true' : 'false'
        });
        const res = await fetch(`/api/obras/reporte-insumos?${params.toString()}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        reporteInsumos.value = data;
        // Expandir todos los frentes por defecto para visibilidad completa
        if (data.frentes && Array.isArray(data.frentes)) {
          data.frentes.forEach(f => {
            frentesExpandidos.value[f.id] = true;
          });
        }
      } catch (e) {
        console.error('Error cargando reporte de insumos:', e);
        reporteInsumos.value = null;
      } finally {
        cargandoReporteInsumos.value = false;
      }
    };

    const buscarReporteObra = async (forzar = false) => {
      const folio = filtroFolioOC.value.trim();
      if (!folio) {
        await cargarReporteInsumos(forzar);
        return;
      }
      if (!obraSeleccionada.value) return;

      const clave = String(obraSeleccionada.value.clave || obraSeleccionada.value.id_obra).toUpperCase();
      modoBusquedaFolioOC.value = true;
      busquedaFolioEjecutada.value = true;
      ordenesCompraPorFolio.value = [];
      errorBusquedaFolioOC.value = '';
      reporteInsumos.value = null;
      cargandoReporteInsumos.value = true;
      try {
        const params = new URLSearchParams({ obra: clave, folio });
        const res = await fetch(`/api/obras/ordenes-compra?${params.toString()}`);
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || `HTTP ${res.status}`);
        }
        ordenesCompraPorFolio.value = data.ordenes_compra || [];
      } catch (e) {
        console.error('Error buscando orden de compra por folio:', e);
        errorBusquedaFolioOC.value = e.message || 'No se pudo consultar el folio.';
      } finally {
        cargandoReporteInsumos.value = false;
      }
    };

    const alCambiarFolioOC = () => {
      modoBusquedaFolioOC.value = !!filtroFolioOC.value.trim();
      busquedaFolioEjecutada.value = false;
      ordenesCompraPorFolio.value = [];
      errorBusquedaFolioOC.value = '';
    };

    const limpiarFiltrosInsumos = () => {
      filtroInsumoClave.value = '';
      filtroInsumoNombre.value = '';
      filtroFolioOC.value = '';
      buscarReporteObra(false);
    };

    const filtrarPorTagInsumo = (tag) => {
      filtroInsumoClave.value = '';
      filtroInsumoNombre.value = tag;
      filtroFolioOC.value = '';
      buscarReporteObra(false);
    };

    const verMovimientos = async (partida, insumo, tipoInicial = 'OC') => {
      if (!obraSeleccionada.value || !partida || !insumo) return;
      const clave = String(obraSeleccionada.value.clave || obraSeleccionada.value.id_obra).toUpperCase();
      insumoMovimientoSeleccionado.value = { partida, insumo };
      tabMovimientos.value = tipoInicial;
      modalMovimientosVisible.value = true;
      cargandoMovimientos.value = true;
      movimientosActuales.value = { requisiciones: [], ordenes_compra: [] };
      try {
        const params = new URLSearchParams({
          obra: clave,
          partida: partida.codigo || partida.id || '',
          insumo: insumo.clave || ''
        });
        const res = await fetch(`/api/obras/movimientos?${params.toString()}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        movimientosActuales.value = await res.json();
      } catch (e) {
        console.error('Error cargando movimientos de insumo:', e);
      } finally {
        cargandoMovimientos.value = false;
      }
    };

    const cerrarModalMovimientos = () => {
      modalMovimientosVisible.value = false;
      insumoMovimientoSeleccionado.value = null;
    };

    const suministrarInsumosObra = async () => {
      if (!obraSeleccionada.value || suministrandoObra.value) return;
      const clave = String(obraSeleccionada.value.clave || obraSeleccionada.value.id_obra).toUpperCase();
      if (!confirm(`¿Deseas suministrar masivamente los insumos actualizables para la obra ${clave} en Aryve?`)) {
        return;
      }
      suministrandoObra.value = true;
      try {
        const res = await fetch('/api/obras/suministrar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ obra: clave })
        });
        const data = await res.json();
        if (data.ok) {
          alert(`✅ Suministro completado: ${data.filas_actualizadas || 0} filas actualizadas.`);
          await cargarReporteInsumos(false);
        } else {
          alert(`⚠️ Aviso: ${data.mensaje || 'No se realizaron cambios'}`);
        }
      } catch (e) {
        alert(`❌ Error al suministrar: ${e.message}`);
      } finally {
        suministrandoObra.value = false;
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
        buscarReporteObra(false);
        return;
      }

      cargandoArbolObra.value = true;
      try {
        const res = await fetch(`/api/obras/${encodeURIComponent(clave)}/arbol`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        cacheArbolesObras.set(clave, data);
        buscarReporteObra(false);
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

    
    // ========================================================
    // REPARADOR DE PRESUPUESTO KONTROL (BOT ANTI-BLOQUEO OC)
    // ========================================================
    const modalRepararVisible = ref(false);
    const reparandoPresupuesto = ref(false);
    const diagnosticandoPresupuesto = ref(false);
    const diagnosticoEjecutado = ref(false);
    const formReparar = ref({ obra: '', insumo: '', folio_req: '' });
    const diagnosticoTarjetas = ref([]);
    const tarjetasSeleccionadasParaReparar = ref([]);
    const logsReparacion = ref([]);
    const resultadoReparacion = ref(null);

    const abrirModalRepararPresupuesto = () => {
      formReparar.value.obra = obraSeleccionada.value ? obraSeleccionada.value.clave : 'KB5';
      formReparar.value.insumo = filtroInsumoClave.value || '1040025';
      formReparar.value.folio_req = filtroFolioOC.value || '';
      diagnosticoTarjetas.value = [];
      tarjetasSeleccionadasParaReparar.value = [];
      logsReparacion.value = [];
      resultadoReparacion.value = null;
      diagnosticoEjecutado.value = false;
      modalRepararVisible.value = true;
      diagnosticarTarjetas();
    };

    const diagnosticarTarjetas = async () => {
      if (!formReparar.value.obra) return;
      diagnosticandoPresupuesto.value = true;
      diagnosticoEjecutado.value = true;
      diagnosticoTarjetas.value = [];
      tarjetasSeleccionadasParaReparar.value = [];
      try {
        const res = await fetch('/api/obras/reparar-presupuesto/diagnostico', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formReparar.value)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        diagnosticoTarjetas.value = data.tarjetas || [];
        tarjetasSeleccionadasParaReparar.value = [...(data.tarjetas || [])];
      } catch (e) {
        console.error('Error diagnosticando tarjetas:', e);
        alert(`Error en diagnóstico: ${e.message}`);
      } finally {
        diagnosticandoPresupuesto.value = false;
      }
    };

    const seleccionarTodasTarjetas = (seleccionar) => {
      if (seleccionar) {
        tarjetasSeleccionadasParaReparar.value = [...diagnosticoTarjetas.value];
      } else {
        tarjetasSeleccionadasParaReparar.value = [];
      }
    };

    const ejecutarReparacionPresupuestoBot = async () => {
      if (!formReparar.value.obra || tarjetasSeleccionadasParaReparar.value.length === 0) return;
      reparandoPresupuesto.value = true;
      resultadoReparacion.value = null;
      logsReparacion.value = [];

      const agregarLog = (texto) => {
        const hora = new Date().toLocaleTimeString('es-MX', { hour12: false });
        logsReparacion.value.push({ hora, texto });
      };

      agregarLog(`Iniciando conexión con Chrome REA para obra ${formReparar.value.obra}...`);
      agregarLog(`Se procesarán ${tarjetasSeleccionadasParaReparar.value.length} tarjetas en PptoKontrol.`);

      try {
        const res = await fetch('/api/obras/reparar-presupuesto/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            obra: formReparar.value.obra,
            tarjetas: tarjetasSeleccionadasParaReparar.value
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        resultadoReparacion.value = data;
        agregarLog(`✅ ${data.mensaje || 'Reparación completada con éxito.'}`);
        setTimeout(() => {
          buscarReporteObra(true);
        }, 1500);
      } catch (e) {
        console.error('Error ejecutando bot reparador:', e);
        resultadoReparacion.value = { ok: false, error: e.message };
        agregarLog(`❌ Error: ${e.message}`);
      } finally {
        reparandoPresupuesto.value = false;
      }
    };

    // ==========================================
    // NAVEGACIÓN AUTOMATIZADA: IR A OBRA EN ARYVE
    // Busca en /scco/Obra, abre panel lateral,
    // clic en APLICAR CONFIGURACIÓN y clic en IR A OBRA
    // ==========================================
    const modalIrAObraVisible = ref(false);
    const ejecutandoIrAObra = ref(false);
    const obraDestinoAryve = ref('');
    const logsIrAObra = ref([]);
    const resultadoIrAObra = ref(null);

    const abrirModalIrAObra = (clave) => {
      const c = clave || (obraSeleccionada.value ? obraSeleccionada.value.clave : 'KB5');
      obraDestinoAryve.value = c;
      logsIrAObra.value = [];
      resultadoIrAObra.value = null;
      modalIrAObraVisible.value = true;
    };

    const ejecutarIrAObraEnAryve = async (clave) => {
      const c = clave || obraDestinoAryve.value;
      if (!c) return;
      obraDestinoAryve.value = c;
      ejecutandoIrAObra.value = true;
      resultadoIrAObra.value = null;
      logsIrAObra.value = [];
      modalIrAObraVisible.value = true;

      const agregarLog = (texto) => {
        const hora = new Date().toLocaleTimeString('es-MX', { hour12: false });
        logsIrAObra.value.push({ hora, texto });
      };

      agregarLog('Iniciando automatización para ingresar a la obra ' + c + ' en Aryve...');
      agregarLog('Comprobando sesión activa en Chrome (puerto 9222) o credenciales de .env...');

      try {
        const res = await fetch('/api/obras/ir-a-obra', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ obra: c })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));

        resultadoIrAObra.value = data;
        if (data.logs && Array.isArray(data.logs)) {
          data.logs.forEach(l => agregarLog(l));
        }
        agregarLog('✅ Proceso finalizado exitosamente. URL destino: ' + (data.url_final || ''));
      } catch (e) {
        console.error('Error al ir a obra en Aryve:', e);
        resultadoIrAObra.value = { ok: false, error: e.message };
        agregarLog('❌ Error: ' + e.message);
      } finally {
        ejecutandoIrAObra.value = false;
      }
    };

    // ==========================================
    // APARTADO: OPTIMIZACIÓN DE INSUMOS (EK10)
    // Previene error de material no disponible en EK10
    // ==========================================
    const gruposInsumosTipo = ref([]);
    const cargandoGruposInsumos = ref(false);
    const filtroGruposInsumos = ref('');
    const seleccionGruposInsumos = ref({});
    const tiposExpandidosOptimizacion = ref({});
    const colaObrasOptimizacion = ref([]);
    const inputNuevaObraOptimizacion = ref('');
    const obraSelectOptimizacion = ref('');
    const ejecutandoOptimizacion = ref(false);

    const cargarGruposInsumosTipo = async () => {
      cargandoGruposInsumos.value = true;
      try {
        const res = await fetch('/api/obras/grupos-insumos-tipo');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const lista = data.GRUPO_INSUMOS_TIPO || [];
        gruposInsumosTipo.value = lista;
        
        // Inicializar checks: por defecto marcar todos excepto los que digan 'Disponible / No usar'
        const sel = {};
        const expandidos = {};
        lista.forEach((item, idx) => {
          expandidos[item.tipo] = idx === 0; // Por defecto expandir el primero (MATERIALES)
          if (Array.isArray(item.datos)) {
            item.datos.forEach(hijo => {
              const key = `${item.tipo}:::${hijo}`;
              if (!hijo.toLowerCase().includes('disponible') && !hijo.toLowerCase().includes('no usar')) {
                sel[key] = true;
              } else {
                sel[key] = false;
              }
            });
          }
        });
        seleccionGruposInsumos.value = sel;
        tiposExpandidosOptimizacion.value = expandidos;
      } catch (e) {
        console.error('Error cargando grupos de insumos:', e);
      } finally {
        cargandoGruposInsumos.value = false;
      }
    };

    const toggleTipoOptimizacion = (tipoNombre) => {
      tiposExpandidosOptimizacion.value[tipoNombre] = !tiposExpandidosOptimizacion.value[tipoNombre];
    };

    const esHijoSeleccionado = (tipoNombre, hijoNombre) => {
      return !!seleccionGruposInsumos.value[`${tipoNombre}:::${hijoNombre}`];
    };

    const toggleHijoInsumo = (tipoNombre, hijoNombre) => {
      const key = `${tipoNombre}:::${hijoNombre}`;
      seleccionGruposInsumos.value[key] = !seleccionGruposInsumos.value[key];
    };

    const contarHijosSeleccionadosTipo = (tipo) => {
      if (!tipo || !Array.isArray(tipo.datos)) return 0;
      return tipo.datos.filter(h => !!seleccionGruposInsumos.value[`${tipo.tipo}:::${h}`]).length;
    };

    const esTipoTotalmenteSeleccionado = (tipo) => {
      if (!tipo || !Array.isArray(tipo.datos)) return false;
      const validos = tipo.datos.filter(h => !h.toLowerCase().includes('disponible') && !h.toLowerCase().includes('no usar'));
      if (validos.length === 0) return false;
      return validos.every(h => !!seleccionGruposInsumos.value[`${tipo.tipo}:::${h}`]);
    };

    const toggleTodosHijosDeTipo = (tipo) => {
      const todos = esTipoTotalmenteSeleccionado(tipo);
      const nuevoEstado = !todos;
      tipo.datos.forEach(h => {
        if (!h.toLowerCase().includes('disponible') && !h.toLowerCase().includes('no usar')) {
          seleccionGruposInsumos.value[`${tipo.tipo}:::${h}`] = nuevoEstado;
        }
      });
    };

    const marcarTodosGruposInsumos = () => {
      gruposInsumosTipo.value.forEach(item => {
        item.datos.forEach(h => {
          if (!h.toLowerCase().includes('disponible') && !h.toLowerCase().includes('no usar')) {
            seleccionGruposInsumos.value[`${item.tipo}:::${h}`] = true;
          }
        });
      });
    };

    const desmarcarTodosGruposInsumos = () => {
      gruposInsumosTipo.value.forEach(item => {
        item.datos.forEach(h => {
          seleccionGruposInsumos.value[`${item.tipo}:::${h}`] = false;
        });
      });
    };

    const seleccionarSoloMateriales = () => {
      gruposInsumosTipo.value.forEach(item => {
        const esMateriales = item.tipo.toLowerCase().includes('materiales');
        item.datos.forEach(h => {
          if (esMateriales && !h.toLowerCase().includes('disponible') && !h.toLowerCase().includes('no usar')) {
            seleccionGruposInsumos.value[`${item.tipo}:::${h}`] = true;
          } else {
            seleccionGruposInsumos.value[`${item.tipo}:::${h}`] = false;
          }
        });
      });
      tiposExpandidosOptimizacion.value['Tipo 1:MATERIALES'] = true;
    };

    const totalGruposInsumosSeleccionados = computed(() => {
      return Object.values(seleccionGruposInsumos.value).filter(Boolean).length;
    });

    const gruposInsumosFiltrados = computed(() => {
      const q = filtroGruposInsumos.value.trim().toLowerCase();
      if (!q) return gruposInsumosTipo.value;

      return gruposInsumosTipo.value.map(tipo => {
        const tipoMatch = tipo.tipo.toLowerCase().includes(q);
        const hijosFiltrados = (tipo.datos || []).filter(h => h.toLowerCase().includes(q));
        if (tipoMatch) {
          return tipo;
        }
        if (hijosFiltrados.length > 0) {
          return {
            ...tipo,
            datos: hijosFiltrados
          };
        }
        return null;
      }).filter(Boolean);
    });

    const agregarObraActualACola = () => {
      if (!obraSeleccionada.value) return;
      agregarObraACola(obraSeleccionada.value);
    };

    const agregarObraACola = (obraObj) => {
      if (!obraObj) return;
      const clave = String(obraObj.clave || obraObj.id_obra || '').trim().toUpperCase();
      if (!clave) return;

      const yaExiste = colaObrasOptimizacion.value.some(o => o.clave === clave);
      if (yaExiste) {
        alert(`La obra ${clave} ya se encuentra en la lista.`);
        return;
      }

      colaObrasOptimizacion.value.push({
        id: Date.now() + Math.random(),
        id_obra: obraObj.id_obra || clave,
        clave: clave,
        nombre: obraObj.nombre || `Obra ${clave}`,
        estatus: 'PENDIENTE',
        mensaje: 'En espera'
      });
    };

    const agregarObraPorInputManual = () => {
      const clave = inputNuevaObraOptimizacion.value.trim().toUpperCase();
      if (!clave) return;

      const encontrada = obrasCatalogo.value.find(o => String(o.clave || o.id_obra).toUpperCase() === clave);
      if (encontrada) {
        agregarObraACola(encontrada);
      } else {
        agregarObraACola({ clave, id_obra: clave, nombre: `Obra ${clave}` });
      }
      inputNuevaObraOptimizacion.value = '';
    };

    const agregarObraPorSelect = () => {
      const clave = obraSelectOptimizacion.value;
      if (!clave) return;
      const encontrada = obrasCatalogo.value.find(o => String(o.clave || o.id_obra).toUpperCase() === clave);
      if (encontrada) {
        agregarObraACola(encontrada);
      }
      obraSelectOptimizacion.value = '';
    };

    const eliminarObraDeCola = (index) => {
      colaObrasOptimizacion.value.splice(index, 1);
    };

    const limpiarColaObras = () => {
      colaObrasOptimizacion.value = [];
    };

        const iniciarOptimizacionObras = async () => {
      if (!colaObrasOptimizacion.value.length) {
        alert('Agrega al menos una obra a la lista para comenzar.');
        return;
      }
      if (totalGruposInsumosSeleccionados.value === 0) {
        alert('Debes marcar al menos un grupo de insumos.');
        return;
      }

      const obrasAProcesar = colaObrasOptimizacion.value.map(o => o.clave);
      const gruposAInyectar = [];
      gruposInsumosTipo.value.forEach(t => {
        if (Array.isArray(t.datos)) {
          t.datos.forEach(hijo => {
            const k = `${t.tipo}:::${hijo}`;
            if (seleccionGruposInsumos.value[k]) {
              gruposAInyectar.push({ tipo: t.tipo, grupo: hijo });
            }
          });
        }
      });

      ejecutandoOptimizacion.value = true;
      obraDestinoAryve.value = obrasAProcesar.join(', ');
      logsIrAObra.value = [];
      resultadoIrAObra.value = null;
      modalIrAObraVisible.value = true;

      const agregarLog = (texto) => {
        const hora = new Date().toLocaleTimeString('es-MX', { hour12: false });
        logsIrAObra.value.push({ hora, texto });
      };

      agregarLog(`Iniciando Optimización de Insumos para ${obrasAProcesar.length} obra(s)...`);
      agregarLog(`Grupos seleccionados para inyección: ${gruposAInyectar.length}`);
      agregarLog(`IMPORTANTE: Al terminar, el bot mantendrá la pantalla en edición SIN GUARDAR.`);

      colaObrasOptimizacion.value.forEach(o => o.estado = 'PROCESANDO...');

      try {
        const res = await fetch('/api/obras/optimizar-insumos/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            obras: obrasAProcesar,
            grupos: gruposAInyectar
          })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

        resultadoIrAObra.value = data;
        if (data.logs && Array.isArray(data.logs)) {
          data.logs.forEach(l => agregarLog(l));
        }

        colaObrasOptimizacion.value.forEach(o => o.estado = 'COMPLETADA (SIN GUARDAR)');
        agregarLog(`✅ ¡Llenado completado exitosamente! Pantalla en edición lista para revisión (SIN GUARDAR).`);
      } catch (e) {
        console.error('Error ejecutando optimización:', e);
        resultadoIrAObra.value = { ok: false, error: e.message };
        colaObrasOptimizacion.value.forEach(o => o.estado = 'ERROR');
        agregarLog(`❌ Error: ${e.message}`);
      } finally {
        ejecutandoOptimizacion.value = false;
      }
    };

    onMounted(() => {
      // 1. Carga escalonada (Waterfall) para evitar saturación de sockets concurrentes (cuellos de botella)
      cargarMetricas();
      setTimeout(cargarUsuarios, 70);
      setTimeout(cargarPuestos, 150);
      setTimeout(cargarProyectosTorre, 230);

      // Carga en diferido de vistas secundarias
      setTimeout(cargarPermisos, 350);
      setTimeout(cargarProvContraRegistros, 450);
      setTimeout(cargarCatalogoObras, 650);
      setTimeout(cargarGruposInsumosTipo, 750);

      // 2. Polling inteligente de Torre de Control: solo si la ventana está visible
      setInterval(() => {
        if (!document.hidden) {
          cargarProyectosTorre();
        }
      }, 6000);

      // 4. Page Visibility API: pausa llamadas cuando el usuario minimiza o cambia de ventana
      document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
          if (vistaActiva.value === 'PROV_CONTRA') {
            cargarProvContraRegistros();
          } else if (vistaActiva.value === 'USUARIOS') {
            cargarUsuarios();
          }
          cargarProyectosTorre();
        }
      });
    });


    // ==========================================
    // SISTEMA DE CHAT DE EQUIPO ESTILO WHATSAPP
    // ==========================================
    const chatAbierto = ref(false);
    const chatMinimizado = ref(false);
    const chatPestanaActiva = ref('mensajes'); // 'mensajes', 'grupos', 'contactos'
    const conversacionAbierta = ref(null); // null = lista de chats/grupos; objeto = chat abierto
    const canalActivo = ref('general');
    const contactoActivo = ref(null); // null si es canal general
    const chatMensajes = ref([]);
    const chatNuevoTexto = ref('');
    const chatEnviando = ref(false);
    const chatUsuariosPresencia = ref([]);
    const chatResumen = ref({ general: { no_leidos: 0, ultimo_mensaje: null }, dms_no_leidos: {} });
    const chatConversaciones = ref([]); // Lista de chats activos desde el backend
    const chatsIniciadosLocal = ref([]); // Chats guardados localmente
    const filtroBusquedaChats = ref('');
    const filtroContactoChat = ref('');
    const filtroBuscarMiPerfil = ref('');
    const chatPerfilModalAbierto = ref(false);

    // Perfil del usuario local (con resolución automática desde /api/chat/mi-identidad)
    const chatUsuarioActual = ref({
      id: '',
      nombre: 'Cargando perfil...',
      puesto: '',
      area: '',
      es_torre: false
    });

    const listaUsuariosParaPerfil = computed(() => {
      const q = (filtroBuscarMiPerfil.value || '').trim().toLowerCase();
      const todos = usuarios.value || [];
      if (!q) return todos.slice(0, 40);
      return todos.filter(u => {
        const nom = (u.nombre_completo || `${u.nombre || ''} ${u.apellidos || ''}`).toLowerCase();
        const pto = (u.puesto || '').toLowerCase();
        const mail = (u.correo || u.email || u.clave || '').toLowerCase();
        return nom.includes(q) || pto.includes(q) || mail.includes(q);
      }).slice(0, 50);
    });

    const inicializarIdentidadChat = async () => {
      try {
        const res = await fetch('/api/chat/mi-identidad');
        if (res.ok) {
          const data = await res.json();
          if (data && data.ok) {
            if (data.es_master && data.usuario) {
              // En Torre de Control (Master) siempre es Esteban
              chatUsuarioActual.value = data.usuario;
              try { localStorage.setItem('chat_perfil_usuario', JSON.stringify(data.usuario)); } catch (e) {}
              return;
            } else if (!data.es_master && data.encontrado && data.usuario) {
              // Cliente reconocido automáticamente por su .env o usuario Windows (ej. Claudia)
              chatUsuarioActual.value = data.usuario;
              try { localStorage.setItem('chat_perfil_usuario', JSON.stringify(data.usuario)); } catch (e) {}
              return;
            } else if (!data.es_master) {
              // Cliente cuyo correo no está en .env o aún no se ha identificado
              const guardado = localStorage.getItem('chat_perfil_usuario');
              if (guardado) {
                try {
                  const p = JSON.parse(guardado);
                  if (p && p.id && p.id !== '1' && p.nombre && !p.nombre.includes('Esteban')) {
                    chatUsuarioActual.value = p;
                    return;
                  }
                } catch (e) {}
              }
              // Si no tiene perfil válido de compañero, abrir modal para que elija su nombre
              chatPerfilModalAbierto.value = true;
              return;
            }
          }
        }
      } catch (e) {
        console.warn('Error resolviendo mi identidad:', e);
      }

      // Fallback localStorage seguro (evitando que un cliente se quede como Esteban)
      try {
        const guardado = localStorage.getItem('chat_perfil_usuario');
        if (guardado) {
          const p = JSON.parse(guardado);
          if (p && p.id) {
            chatUsuarioActual.value = p;
          }
        }
      } catch (e) {}
    };

    inicializarIdentidadChat();

    const chatTotalNoLeidos = computed(() => {
      let tot = (chatResumen.value.general && chatResumen.value.general.no_leidos) || 0;
      if (chatResumen.value.dms_no_leidos) {
        for (const k in chatResumen.value.dms_no_leidos) {
          tot += chatResumen.value.dms_no_leidos[k] || 0;
        }
      }
      return tot;
    });

    const listaContactosFiltrada = computed(() => {
      const q = (filtroContactoChat.value || '').trim().toLowerCase();
      const mapa = new Map();
      (chatUsuariosPresencia.value || []).forEach(u => {
        if (String(u.usuario_id) !== String(chatUsuarioActual.value.id)) {
          mapa.set(String(u.usuario_id), { ...u });
        }
      });

      const todos = usuarios.value || [];
      const fuente = q ? todos.filter(u => {
        const nom = (u.nombre_completo || `${u.nombre || ''} ${u.apellidos || ''}`).toLowerCase();
        const pto = (u.puesto || '').toLowerCase();
        return nom.includes(q) || pto.includes(q);
      }).slice(0, 50) : todos.slice(0, 60);

      fuente.forEach(u => {
        const uid = String(u.id);
        if (uid !== String(chatUsuarioActual.value.id) && !mapa.has(uid)) {
          mapa.set(uid, {
            usuario_id: uid,
            nombre: u.nombre_completo || `${u.nombre || ''} ${u.apellidos || ''}`.trim() || 'Colaborador',
            puesto: u.puesto || 'Puesto no esp.',
            area: u.area_organizacion || '',
            es_torre: false,
            en_linea: false
          });
        }
      });
      const arr = Array.from(mapa.values());
      if (!q) return arr;
      return arr.filter(c => 
        c.nombre.toLowerCase().includes(q) || 
        (c.puesto && c.puesto.toLowerCase().includes(q))
      );
    });

    const cargarChatsIniciadosLocal = () => {
      try {
        const key = 'chats_iniciados_' + (chatUsuarioActual.value?.id || '1');
        const guardado = localStorage.getItem(key);
        if (guardado) {
          chatsIniciadosLocal.value = JSON.parse(guardado) || [];
        }
      } catch (e) {}
    };

    const guardarChatIniciado = (contacto) => {
      if (!contacto) return;
      const cid = String(contacto.usuario_id || contacto.contacto_id);
      const existe = chatsIniciadosLocal.value.some(c => String(c.contacto_id || c.usuario_id) === cid);
      if (!existe) {
        chatsIniciadosLocal.value.unshift({
          canal: canalDirectoId(chatUsuarioActual.value.id, cid),
          contacto_id: cid,
          contacto_nombre: contacto.nombre || contacto.contacto_nombre,
          contacto_puesto: contacto.puesto || contacto.contacto_puesto || 'Colaborador',
          contacto_area: contacto.area || contacto.contacto_area || '',
          ultimo_texto: 'Chat iniciado...',
          es_mio: true,
          hora_corta: 'Reciente',
          no_leidos: 0,
          en_linea: !!contacto.en_linea
        });
        try {
          const key = 'chats_iniciados_' + (chatUsuarioActual.value?.id || '1');
          localStorage.setItem(key, JSON.stringify(chatsIniciadosLocal.value));
        } catch (e) {}
      }
    };

    const cargarConversaciones = async () => {
      if (!chatUsuarioActual.value?.id) return;
      try {
        const res = await fetch(`/api/chat/conversaciones?usuario_id=${chatUsuarioActual.value.id}`);
        if (res.ok) {
          const d = await res.json();
          chatConversaciones.value = d.conversaciones || [];
        }
      } catch (e) {}
    };

    const listaConversacionesUnificadas = computed(() => {
      const mapa = new Map();
      (chatConversaciones.value || []).forEach(c => {
        mapa.set(String(c.contacto_id), { ...c });
      });
      (chatsIniciadosLocal.value || []).forEach(c => {
        const cid = String(c.contacto_id || c.usuario_id);
        if (!mapa.has(cid)) {
          mapa.set(cid, { ...c });
        }
      });
      const arr = Array.from(mapa.values());
      const q = (filtroBusquedaChats.value || '').trim().toLowerCase();
      if (!q) return arr;
      return arr.filter(c => 
        (c.contacto_nombre && c.contacto_nombre.toLowerCase().includes(q)) ||
        (c.ultimo_texto && c.ultimo_texto.toLowerCase().includes(q)) ||
        (c.contacto_puesto && c.contacto_puesto.toLowerCase().includes(q))
      );
    });

    const abrirConversacionDirecta = (c) => {
      const cid = String(c.contacto_id || c.usuario_id);
      contactoActivo.value = {
        usuario_id: cid,
        nombre: c.contacto_nombre || c.nombre,
        puesto: c.contacto_puesto || c.puesto || '',
        area: c.contacto_area || c.area || '',
        en_linea: !!c.en_linea
      };
      canalActivo.value = c.canal || canalDirectoId(chatUsuarioActual.value.id, cid);
      conversacionAbierta.value = {
        tipo: 'dm',
        id: cid,
        nombre: contactoActivo.value.nombre,
        puesto: contactoActivo.value.puesto,
        en_linea: contactoActivo.value.en_linea
      };
      guardarChatIniciado(contactoActivo.value);
      chatPestanaActiva.value = 'mensajes';
      cargarMensajesCanal(true);
    };

    const iniciarChatDesdeDirectorio = (contacto) => {
      guardarChatIniciado(contacto);
      abrirConversacionDirecta(contacto);
    };

    const abrirGrupoGeneral = () => {
      canalActivo.value = 'general';
      contactoActivo.value = null;
      conversacionAbierta.value = {
        tipo: 'grupo',
        id: 'general',
        nombre: '📢 Sala General (Todo el Equipo)'
      };
      chatPestanaActiva.value = 'grupos';
      cargarMensajesCanal(true);
    };

    const volverALista = () => {
      conversacionAbierta.value = null;
      contactoActivo.value = null;
      cargarConversaciones();
      cargarPresenciaYResumen();
    };

    const scrollChatAlFinal = () => {
      setTimeout(() => {
        const box = document.getElementById('chat-mensajes-container');
        if (box) box.scrollTop = box.scrollHeight;
      }, 50);
    };

    let ultimoConteoNoLeidos = 0;
    const reproducirSonidoNotificacion = () => {
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, ctx.currentTime); // Nota D5
        osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // Nota A5
        gain.gain.setValueAtTime(0.12, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.25);
      } catch (e) {}
    };

    const canalDirectoId = (u1, u2) => {
      const a = String(u1).trim().toLowerCase();
      const b = String(u2).trim().toLowerCase();
      return `dm_${a < b ? a : b}__${a < b ? b : a}`;
    };

    const cargarPresenciaYResumen = async () => {
      try {
        await fetch('/api/chat/presencia', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            usuario_id: String(chatUsuarioActual.value.id),
            nombre: chatUsuarioActual.value.nombre,
            puesto: chatUsuarioActual.value.puesto || '',
            area: chatUsuarioActual.value.area || '',
            es_torre: !!chatUsuarioActual.value.es_torre
          })
        });

        const resUsers = await fetch(`/api/chat/usuarios?usuario_actual=${chatUsuarioActual.value.id}`);
        if (resUsers.ok) {
          const d = await resUsers.json();
          chatUsuariosPresencia.value = d.usuarios || [];
        }

        const resResumen = await fetch(`/api/chat/resumen?usuario_id=${chatUsuarioActual.value.id}`);
        if (resResumen.ok) {
          const d = await resResumen.json();
          chatResumen.value = d.resumen || { general: { no_leidos: 0 }, dms_no_leidos: {} };

          // Notificación visual en pestaña del navegador estilo WhatsApp Web
          const tot = chatTotalNoLeidos.value;
          if (tot > 0) {
            document.title = `💬 (${tot}) Mensaje nuevo | Dashboard`;
            if (tot > ultimoConteoNoLeidos) {
              reproducirSonidoNotificacion();
            }
          } else {
            document.title = 'Dashboard Intelligence Solutions - VELAS';
          }
          ultimoConteoNoLeidos = tot;
        }

        // Actualizar lista de conversaciones activas estilo WhatsApp
        cargarConversaciones();
      } catch (e) {}
    };

    const cargarMensajesCanal = async (autoScroll = false) => {
      try {
        const res = await fetch(`/api/chat/mensajes?canal=${canalActivo.value}&limite=80`);
        if (res.ok) {
          const d = await res.json();
          const anteriores = chatMensajes.value.length;
          chatMensajes.value = d.mensajes || [];
          if (autoScroll || chatMensajes.value.length !== anteriores) {
            scrollChatAlFinal();
          }
          await fetch('/api/chat/leido', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              canal: canalActivo.value,
              usuario_id: String(chatUsuarioActual.value.id)
            })
          });
        }
      } catch (e) {}
    };

    const seleccionarCanalGeneral = () => {
      canalActivo.value = 'general';
      contactoActivo.value = null;
      chatPestanaActiva.value = 'chat';
      cargarMensajesCanal(true);
    };

    const seleccionarContactoDirecto = (contacto) => {
      contactoActivo.value = contacto;
      canalActivo.value = canalDirectoId(chatUsuarioActual.value.id, contacto.usuario_id);
      chatPestanaActiva.value = 'chat';
      cargarMensajesCanal(true);
    };

    const enviarMensajeChat = async () => {
      const txt = chatNuevoTexto.value.trim();
      if (!txt || chatEnviando.value) return;
      chatEnviando.value = true;
      try {
        const payload = {
          canal: canalActivo.value,
          remitente_id: String(chatUsuarioActual.value.id),
          remitente_nombre: chatUsuarioActual.value.nombre,
          remitente_rol: chatUsuarioActual.value.puesto || (chatUsuarioActual.value.es_torre ? 'Torre' : 'Colaborador'),
          texto: txt,
          destinatario_id: contactoActivo.value ? String(contactoActivo.value.usuario_id) : '',
          destinatario_nombre: contactoActivo.value ? contactoActivo.value.nombre : ''
        };
        const res = await fetch('/api/chat/enviar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          chatNuevoTexto.value = '';
          await cargarMensajesCanal(true);
        }
      } catch (e) {
        console.error('Error enviando mensaje:', e);
      } finally {
        chatEnviando.value = false;
      }
    };

    const toggleChat = () => {
      chatAbierto.value = !chatAbierto.value;
      if (chatAbierto.value) {
        chatMinimizado.value = false;
        cargarChatsIniciadosLocal();
        cargarConversaciones();
        cargarPresenciaYResumen();
        if (conversacionAbierta.value) {
          cargarMensajesCanal(true);
        }
      }
    };

    const guardarPerfilChat = (usuario) => {
      if (!usuario) return;
      chatUsuarioActual.value = {
        id: String(usuario.id || 'usr_' + Date.now()),
        nombre: usuario.nombre_completo || usuario.nombre || 'Colaborador',
        puesto: usuario.puesto || 'Colaborador',
        area: usuario.area_organizacion || 'General',
        es_torre: String(usuario.id) === '1' || String(usuario.nombre).toLowerCase().includes('administrador')
      };
      try {
        localStorage.setItem('chat_perfil_usuario', JSON.stringify(chatUsuarioActual.value));
      } catch (e) {}
      chatPerfilModalAbierto.value = false;
      cargarPresenciaYResumen();
      cargarConversaciones();
      if (contactoActivo.value) {
        canalActivo.value = canalDirectoId(chatUsuarioActual.value.id, contactoActivo.value.usuario_id);
        cargarMensajesCanal(true);
      }
    };

    // Polling periodico ligero
    setInterval(() => {
      cargarPresenciaYResumen();
      cargarConversaciones();
      if (chatAbierto.value && !chatMinimizado.value && conversacionAbierta.value) {
        cargarMensajesCanal(false);
      }
    }, 3000);

    return {
      // CHAT DE EQUIPO Y PRIVADOS 1 A 1 ESTILO WHATSAPP
      chatAbierto,
      chatMinimizado,
      chatPestanaActiva,
      conversacionAbierta,
      canalActivo,
      contactoActivo,
      chatMensajes,
      chatNuevoTexto,
      chatEnviando,
      chatUsuariosPresencia,
      chatResumen,
      chatConversaciones,
      filtroBusquedaChats,
      listaConversacionesUnificadas,
      chatTotalNoLeidos,
      chatPerfilModalAbierto,
      chatUsuarioActual,
      filtroContactoChat,
      filtroBuscarMiPerfil,
      listaUsuariosParaPerfil,
      listaContactosFiltrada,
      toggleChat,
      seleccionarCanalGeneral,
      seleccionarContactoDirecto,
      abrirConversacionDirecta,
      iniciarChatDesdeDirectorio,
      abrirGrupoGeneral,
      volverALista,
      enviarMensajeChat,
      guardarPerfilChat,
      cargarMensajesCanal,
      // Tema Claro / Oscuro (Persistente)
      temaActual,
      toggleTema,
      aplicarTema,

      // Navegación Automatizada Aryve (Ir a Obra)
      modalIrAObraVisible,
      ejecutandoIrAObra,
      obraDestinoAryve,
      logsIrAObra,
      resultadoIrAObra,
      abrirModalIrAObra,
      ejecutarIrAObraEnAryve,

      // Optimización de Insumos (EK10)
      gruposInsumosTipo,
      cargandoGruposInsumos,
      filtroGruposInsumos,
      seleccionGruposInsumos,
      tiposExpandidosOptimizacion,
      colaObrasOptimizacion,
      inputNuevaObraOptimizacion,
      obraSelectOptimizacion,
      ejecutandoOptimizacion,
      cargarGruposInsumosTipo,
      toggleTipoOptimizacion,
      esHijoSeleccionado,
      toggleHijoInsumo,
      contarHijosSeleccionadosTipo,
      esTipoTotalmenteSeleccionado,
      toggleTodosHijosDeTipo,
      marcarTodosGruposInsumos,
      desmarcarTodosGruposInsumos,
      seleccionarSoloMateriales,
      totalGruposInsumosSeleccionados,
      gruposInsumosFiltrados,
      agregarObraActualACola,
      agregarObraACola,
      agregarObraPorInputManual,
      agregarObraPorSelect,
      eliminarObraDeCola,
      limpiarColaObras,
      iniciarOptimizacionObras,

      // Reparador de Presupuesto Bot
      modalRepararVisible,
      reparandoPresupuesto,
      diagnosticandoPresupuesto,
      diagnosticoEjecutado,
      formReparar,
      diagnosticoTarjetas,
      tarjetasSeleccionadasParaReparar,
      logsReparacion,
      resultadoReparacion,
      abrirModalRepararPresupuesto,
      diagnosticarTarjetas,
      seleccionarTodasTarjetas,
      ejecutarReparacionPresupuestoBot,

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

      // Insumos & Órdenes de Compra (Clon REA)
      filtroInsumoClave,
      filtroInsumoNombre,
      filtroFolioOC,
      modoBusquedaFolioOC,
      busquedaFolioEjecutada,
      ordenesCompraPorFolio,
      errorBusquedaFolioOC,
      reporteInsumos,
      cargandoReporteInsumos,
      suministrandoObra,
            modalMovimientosVisible,
      cargandoMovimientos,
      tabMovimientos,
      movimientosActuales,
      insumoMovimientoSeleccionado,
      cargarReporteInsumos,
      buscarReporteObra,
      alCambiarFolioOC,
      limpiarFiltrosInsumos,
      filtrarPorTagInsumo,
      verMovimientos,
      cerrarModalMovimientos,
      suministrarInsumosObra,
            esMaster,

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
      
      // Proveedores y Contratistas Unificado (EK10 / Aryve)
      provContraRegistros,
      provContraMetricas,
      provContraCargando,
      provContraEjecutando,
      provContraModoReal,
      provContraLector,
      provContraInputNumpro,
      provContraConsultandoDb,
      provContraSubiendoImagen,
      provContraBusqueda,
      provContraFiltro,
      provContraSeleccionados,
      provContraTerminalLogs,
      provContraModalEditor,
      provContraRegistroEditando,
      provContraModalVisor,
      provContraImagenVisorUrl,
      provContraEnRevision,
      provContraEnRevisionCount,
      provContraFiltrados,
      provContraColumnaOrden,
      provContraOrdenAsc,
      provContraMarcadosProveedorCount,
      provContraMarcadosContratistaCount,
      toggleOrdenProvContra,
      verificarRegistroProvContra,
      ejecutarMarcadosProvContra,
      cargarProvContraRegistros,
      consultarProvContraPorNumpro,
      manejarDropCapturaProvContra,
      manejarSeleccionCapturaProvContra,
      subirArchivoCapturaProvContra,
      toggleCasillaRegistro,
      enviarRegistroAHistorial,
      enviarTodosAHistorial,
      toggleSeleccionProvContra,
      toggleSeleccionarTodosProvContra,
      abrirEditorProvContra,
      guardarEdicionProvContra,
      eliminarRegistroProvContra,
      abrirVisorImagenProvContra,
      iniciarEjecucionProvContra,
      limpiarTerminalProvContra,

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
      // Sistema de Actualización Cliente (Equipo) y Modo Master
      esMaster,
      actualizacionDisponibleCliente,
      actualizandoSistema,
      verificarActualizacionCliente,
      ejecutarActualizacionCliente,

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
      // Creacion de Posiciones
      metaPosiciones,
      formCreacionPosicion,
      calculandoClave,
      calcularSiguienteClave,
      dropdownNombreAbierto,
      filtroNombre,
      seleccionarNombrePosicion,
      dropdownCategoriaAbierto,
      filtroCategoria,
      seleccionarCategoriaPosicion,
      formCreacionPosicion,
      guardandoPosicionSimple,
      resultadoCreacionPosicion,
      cargarMetaPosiciones,
      guardarPosicionSimple,
      limpiarFormPosicionSimple,
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
