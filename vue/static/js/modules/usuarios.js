/**
 * Módulo JavaScript Modular: Gestión de Usuarios, Puestos y Clasificadores
 * Archivo: vue/static/js/modules/usuarios.js
 */
(function() {
  window.createUsuariosModule = function(Vue) {
    const { ref, computed } = Vue;

    // Estado principal de usuarios
    const cargando = ref(false);
    const usuarios = ref([]);
    const usuarioSeleccionado = ref(null);
    const filtroBusqueda = ref('');
    const filtroVigencia = ref('TODOS');
    const catalogoPuestos = ref([]);
    const catalogoPuestosDetalle = ref({});
    const metricas = ref({
      total: 0,
      activos: 0,
      vencen_mes: 0,
      vencen_prox: 0,
      vencidos: 0,
      vigencia_indefinida: 0
    });
    const sincronizandoAryve = ref(false);

    // Modal Usuario & Selenium
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

    // Autocomplete Puesto en Nuevo Usuario
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

    const toggleDropdownPuestoNuevoUsuario = () => {
      mostrarDropdownPuestoNuevoUsuario.value = !mostrarDropdownPuestoNuevoUsuario.value;
    };

    // Autocomplete Puesto en Clasificadores
    const busquedaPuestoClasificador = ref('');
    const mostrarDropdownPuestoClasificador = ref(false);
    const puestosFiltradosClasificador = computed(() => {
      const q = busquedaPuestoClasificador.value.trim().toLowerCase();
      if (!q) return catalogoPuestos.value;
      return catalogoPuestos.value.filter(p => p.toLowerCase().includes(q));
    });

    // Clasificadores
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

    // Creación de Posiciones (Consecutivo POS-XXXX)
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

    // ==========================================
    // MÉTODOS DE DATOS: USUARIOS Y PUESTOS
    // ==========================================
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
        catalogoPuestosDetalle.value = data || {};
        catalogoPuestos.value = Object.keys(data).sort();
      } catch (e) {
        console.error('Error cargando puestos:', e);
        if (intentos > 1) setTimeout(() => cargarPuestos(intentos - 1), 1200);
      }
    };

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

    // ==========================================
    // MÉTODOS DE POSICIONES
    // ==========================================
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

    // Modal Alta Usuario / Selenium
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

    // Clasificadores
    const cargarInfoPuesto = async (puesto) => {
      if (!puesto) return { total: 0, area: '', categorias: [], clasificadores: {} };
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

    const cerrarModalClasificador = () => { modalClasificadorAbierto.value = false; };

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

    const toggleDropdownPuestoClasificador = () => {
      mostrarDropdownPuestoClasificador.value = !mostrarDropdownPuestoClasificador.value;
    };

    return {
      cargando,
      usuarios,
      usuarioSeleccionado,
      filtroBusqueda,
      filtroVigencia,
      catalogoPuestos,
      catalogoPuestosDetalle,
      metricas,
      sincronizandoAryve,
      modalUsuarioAbierto,
      formUsuario,
      ejecutandoSelenium,
      estadoBot,
      modalClasificadorAbierto,
      puestoClasificadorSeleccionado,
      puestoClasificadorTemporal,
      infoClasificadorPuesto,
      infoClasificadorTemporal,
      estadoAsignacionClasificadores,
      metaPosiciones,
      formCreacionPosicion,
      calculandoClave,
      dropdownNombreAbierto,
      filtroNombre,
      dropdownCategoriaAbierto,
      filtroCategoria,
      guardandoPosicionSimple,
      resultadoCreacionPosicion,
      busquedaPuestoNuevoUsuario,
      mostrarDropdownPuestoNuevoUsuario,
      busquedaPuestoClasificador,
      mostrarDropdownPuestoClasificador,
      puestosFiltradosNuevoUsuario,
      puestosFiltradosClasificador,
      cargarUsuarios,
      sincronizarUsuariosAryve,
      seleccionarUsuario,
      alBuscar,
      cargarPuestos,
      cargarMetricas,
      abrirModalUsuario,
      cerrarModalUsuario,
      guardarDatosEnFicha,
      editarDatosEnFicha,
      limpiarFormularioUsuario,
      iniciarCreacionSelenium,
      reiniciarCreacionSelenium,
      cargarMetaPosiciones,
      calcularSiguienteClave,
      seleccionarNombrePosicion,
      seleccionarCategoriaPosicion,
      guardarPosicionSimple,
      limpiarFormPosicionSimple,
      cargarClasificadoresUsuario,
      abrirModalClasificador,
      cerrarModalClasificador,
      alCambiarPuestoModalClasificador,
      confirmarSeleccionPuestoClasificador,
      borrarClasificadoresSeleccion,
      iniciarAsignacionClasificadores,
      seleccionarPuestoNuevoUsuario,
      limpiarPuestoNuevoUsuario,
      toggleDropdownPuestoNuevoUsuario,
      seleccionarPuestoModalClasificador,
      limpiarPuestoModalClasificador,
      toggleDropdownPuestoClasificador
    };
  };
})();
