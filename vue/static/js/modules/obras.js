/**
 * Módulo JavaScript Modular: Obras, WBS, Insumos & Órdenes de Compra
 * Archivo: vue/static/js/modules/obras.js
 */
(function() {
  window.createObrasModule = function(Vue) {
    const { ref, computed } = Vue;

    // ==========================================
    // ESTADO OBRAS & WBS (INSUMOS & ORDENES DE COMPRA)
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
    // esMaster provisto globalmente
        const modalMovimientosVisible = ref(false);
    const cargandoMovimientos = ref(false);
    const tabMovimientos = ref('OC');
    const movimientosActuales = ref({ requisiciones: [], ordenes_compra: [] });
    const insumoMovimientoSeleccionado = ref(null);







    // ==========================================
    // MÉTODOS OBRAS & WBS (INSUMOS & ORDENES DE COMPRA)
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



    
    const obrasFiltradas = computed(() => {
      const q = (filtroBusquedaObra.value || '').trim().toUpperCase();
      if (!q) return obrasCatalogo.value || [];
      return (obrasCatalogo.value || []).filter(o => {
        const cve = String(o.clave || '').toUpperCase();
        const nom = String(o.nombre || '').toUpperCase();
        const id = String(o.id_obra || '').toUpperCase();
        return cve.includes(q) || nom.includes(q) || id.includes(q);
      });
    });

    const sincronizandoFirestoreObra = ref(false);
    const sincronizarFirestoreObraActual = async () => {};

        
    const arbolFiltrado = computed(() => {
      if (!arbolObraActual.value || !arbolObraActual.value.frentes) return [];
      const q = (filtroArbolObra.value || '').trim().toUpperCase();
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

            return {
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
    };
  };
})();
