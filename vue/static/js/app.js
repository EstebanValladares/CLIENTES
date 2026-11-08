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
    const esMaster = ref(false);
    const vistaActiva = ref('USUARIOS');

    // NAVEGACIÓN ENTRE VISTAS
    const cambiarVista = (vista) => {
      if (vista === 'MAPEO') {
        if (typeof abrirConsultaFlotante === 'function') {
          abrirConsultaFlotante('MAPEO');
        }
        return;
      }
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


    // ==========================================
    // VISTA MODULAR: USUARIOS (vue/static/js/modules/usuarios.js)
    // ==========================================
    const usuariosModulo = window.createUsuariosModule ? window.createUsuariosModule(Vue) : {};
    const {
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
    } = usuariosModulo;

    // ==========================================
    // VISTA MODULAR: OBRAS & WBS (vue/static/js/modules/obras.js)
    // ==========================================
    const obrasModulo = window.createObrasModule ? window.createObrasModule(Vue) : {};
    const {
      abrirModalIrAObra,
      abrirModalRepararPresupuesto,
      agregarObraACola,
      agregarObraActualACola,
      agregarObraPorInputManual,
      agregarObraPorSelect,
      alCambiarFolioOC,
      arbolFiltrado,
      arbolObraActual,
      buscarReporteObra,
      busquedaFolioEjecutada,
      cacheArbolesObras,
      cargandoArbolObra,
      cargandoGruposInsumos,
      cargandoMovimientos,
      cargandoObras,
      cargandoReporteInsumos,
      cargarCatalogoObras,
      cargarGruposInsumosTipo,
      cargarReporteInsumos,
      cerrarModalMovimientos,
      colaObrasOptimizacion,
      colapsarTodoArbol,
      contarHijosSeleccionadosTipo,
      desmarcarTodosGruposInsumos,
      diagnosticandoPresupuesto,
      diagnosticarTarjetas,
      diagnosticoEjecutado,
      diagnosticoTarjetas,
      ejecutandoIrAObra,
      ejecutandoOptimizacion,
      ejecutarIrAObraEnAryve,
      ejecutarReparacionPresupuestoBot,
      eliminarObraDeCola,
      errorBusquedaFolioOC,
      esHijoSeleccionado,
      esTipoTotalmenteSeleccionado,
      expandirFrenteInicial,
      expandirTodoArbol,
      filtrarPorTagInsumo,
      filtroArbolObra,
      filtroBusquedaObra,
      filtroFolioOC,
      filtroGruposInsumos,
      filtroInsumoClave,
      filtroInsumoNombre,
      formReparar,
      frentesExpandidos,
      gruposInsumosFiltrados,
      gruposInsumosTipo,
      iniciarOptimizacionObras,
      inputNuevaObraOptimizacion,
      insumoMovimientoSeleccionado,
      limpiarColaObras,
      limpiarFiltrosInsumos,
      logsIrAObra,
      logsReparacion,
      marcarTodosGruposInsumos,
      metricasObras,
      modalIrAObraVisible,
      modalMovimientosVisible,
      modalRepararVisible,
      modoBusquedaFolioOC,
      movimientosActuales,
      obraDestinoAryve,
      obraSeleccionada,
      obraSelectOptimizacion,
      obrasCatalogo,
      obrasFiltradas,
      ordenesCompraPorFolio,
      partidasExpandidas,
      recargarObras,
      reparandoPresupuesto,
      reporteInsumos,
      resultadoIrAObra,
      resultadoReparacion,
      seleccionGruposInsumos,
      seleccionarObra,
      seleccionarSoloMateriales,
      seleccionarTodasTarjetas,
      sincronizandoFirestoreObra,
      sincronizandoObras,
      sincronizarFirestoreObraActual,
      sincronizarObrasAryve,
      suministrandoObra,
      suministrarInsumosObra,
      tabMovimientos,
      tarjetasSeleccionadasParaReparar,
      tiposExpandidosOptimizacion,
      toggleFrente,
      toggleHijoInsumo,
      togglePartida,
      toggleTipoOptimizacion,
      toggleTodosHijosDeTipo,
      totalGruposInsumosSeleccionados,
      verMovimientos
    } = obrasModulo;

    // ==========================================
    // VISTA MODULAR: PROYECTOS (vue/static/js/modules/proyectos.js)
    // ==========================================
    const proyectosModulo = window.createProyectosModule ? window.createProyectosModule(Vue) : {};
    const {
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
      iniciarDepuracionPermisos
    } = proyectosModulo;

    // VISTA MODULAR: PROVEEDORES & CONTRATISTAS (vue/static/js/modules/proveedores_contratistas.js)
    // ==========================================
    const provContraModulo = window.createProvContraModule ? window.createProvContraModule(Vue) : {};
    const {
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
      provContraColumnaOrden,
      provContraOrdenAsc,
      provContraTerminalLogs,
      provContraModalEditor,
      provContraRegistroEditando,
      provContraModalVisor,
      provContraImagenVisorUrl,
      provContraEnRevision,
      provContraEnRevisionCount,
      provContraMarcadosProveedorCount,
      provContraMarcadosContratistaCount,
      toggleOrdenProvContra,
      provContraFiltrados,
      cargarProvContraRegistros,
      consultarProvContraPorNumpro,
      manejarDropCapturaProvContra,
      manejarSeleccionCapturaProvContra,
      verificarRegistroProvContra,
      ejecutarMarcadosProvContra,
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
      limpiarTerminalProvContra
    } = provContraModulo;


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
            // Polling periódico para detectar nuevas versiones en clientes cada 30 segundos
            setInterval(verificarActualizacionCliente, 30000);
            window.addEventListener('focus', () => {
              verificarActualizacionCliente();
            });
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

    
    


    // VISTA MODULAR: MAPEO (vue/static/js/modules/mapeo.js)
    // ==========================================
    const mapeoModulo = window.createMapeoModule ? window.createMapeoModule(Vue) : {};
    const {
      metricasMapeo,
      catalogoCCsMapeo,
      lotesMapeo,
      totalLotesMapeoFiltrados,
      cargandoMapeo,
      sincronizandoMapeo,
      filtroMapeoCC,
      filtroMapeoManzana,
      filtroMapeoLote,
      filtroMapeoNoInt,
      filtroMapeoIdEK,
      filtroMapeoBusqueda,
      paginaMapeoActual,
      limiteMapeo,
      totalPaginasMapeo,
      cargarResumenMapeo,
      alCambiarFiltroMapeo,
      consultarLotesMapeo,
      limpiarFiltrosMapeo,
      cambiarPaginaMapeo,
      seleccionarCCMapeo,
      sincronizarMapeoEnkontrol,
      exportarMapeoCSV
    } = mapeoModulo;

    // ==========================================
    // MÓDULO: CONSULTAS FLOTANTES (vue/static/js/modules/consultas_flotantes.js)
    // ==========================================
    const consultasFlotantesModulo = window.createConsultasFlotantesModule ? window.createConsultasFlotantesModule(Vue, {
      cargarResumenMapeo: () => {
        if (typeof cargarResumenMapeo === 'function') cargarResumenMapeo();
      },
      consultarLotesMapeo: () => {
        if (typeof consultarLotesMapeo === 'function') consultarLotesMapeo();
      }
    }) : {};
    const {
      menuConsultasAbierto,
      consultaFlotanteActiva,
      consultaMaximizada,
      catalogoConsultas,
      toggleMenuConsultas,
      abrirConsultaFlotante,
      cerrarConsultaFlotante,
      toggleMaximizarConsulta
    } = consultasFlotantesModulo;

    // ==========================================
    // SISTEMA DE NAVEGACIÓN EN CÁPSULA EXPANDIBLE (BUBBLE DOCK NAV)
    // ==========================================
    const catalogoVistas = computed(() => [
      {
        id: 'USUARIOS',
        nombre: 'Usuarios',
        icono: 'fa-solid fa-users',
        badge: metricas?.value?.total_usuarios || 0
      },
      {
        id: 'PROYECTOS',
        nombre: 'Permisos Proyectos',
        icono: 'fa-solid fa-diagram-project',
        badge: (permisosObras?.value?.length || 0) + ' obras'
      },
      {
        id: 'PROV_CONTRA',
        nombre: 'Proveedores & Contratistas',
        icono: 'fa-solid fa-address-card',
        badge: (provContraEnRevisionCount?.value > 0 
          ? (provContraEnRevisionCount.value + ' por revisar') 
          : (provContraRegistros?.value?.length || 0))
      },
      {
        id: 'OBRAS',
        nombre: 'Obras & Orden de Compra',
        icono: 'fa-solid fa-helmet-safety',
        badge: metricasObras?.value?.total_obras || obrasCatalogo?.value?.length || 0
      }
    ]);

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
      setTimeout(cargarResumenMapeo, 850);

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
          
          // Actualizar estado 'En línea' / 'Desconectado' del contacto que tenemos abierto en pantalla
          if (contactoActivo.value) {
            const cid = String(contactoActivo.value.usuario_id);
            const pres = (chatUsuariosPresencia.value || []).find(u => String(u.usuario_id) === cid);
            if (pres) {
              contactoActivo.value.en_linea = !!pres.en_linea;
              if (conversacionAbierta.value) {
                conversacionAbierta.value.en_linea = !!pres.en_linea;
              }
            }
          }
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
        const uId = encodeURIComponent(String(chatUsuarioActual.value.id || ''));
        const res = await fetch(`/api/chat/mensajes?canal=${canalActivo.value}&limite=80&usuario_id=${uId}`);
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
      catalogoVistas,
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

      // VISTA 5: MAPEO DE LOTES & CENTROS DE COSTOS (ENKONTROL)
      metricasMapeo,
      catalogoCCsMapeo,
      lotesMapeo,
      totalLotesMapeoFiltrados,
      cargandoMapeo,
      sincronizandoMapeo,
      filtroMapeoCC,
      filtroMapeoManzana,
      filtroMapeoLote,
      filtroMapeoNoInt,
      filtroMapeoIdEK,
      filtroMapeoBusqueda,
      paginaMapeoActual,
      limiteMapeo,
      totalPaginasMapeo,
      cargarResumenMapeo,
      alCambiarFiltroMapeo,
      consultarLotesMapeo,
      limpiarFiltrosMapeo,
      cambiarPaginaMapeo,
      seleccionarCCMapeo,
      sincronizarMapeoEnkontrol,
      exportarMapeoCSV,

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
      iniciarAsignacionClasificadores,
      toggleDropdownPuestoNuevoUsuario,
      toggleDropdownPuestoClasificador,
      // Consultas Flotantes Rápidas
      menuConsultasAbierto,
      consultaFlotanteActiva,
      consultaMaximizada,
      catalogoConsultas,
      toggleMenuConsultas,
      abrirConsultaFlotante,
      cerrarConsultaFlotante,
      toggleMaximizarConsulta
    };
  }
}).mount('#app');
