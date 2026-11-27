/**
 * Módulo JavaScript Modular: EK9 - EK10 (Vista Unificada con Carga XLSX)
 * Archivo: vue/static/js/modules/ek9_ek10.js
 */
(function() {
  window.createEk9Ek10Module = function(Vue) {
    const { ref, computed } = Vue;

    const ek9Ek10Cargado = ref(false);
    const ek9Ek10ArchivoNombre = ref('');
    const ek9Ek10Hojas = ref([]);
    const ek9Ek10Ordenes = ref([]);
    const ek9Ek10Detalle = ref([]);

    const cargandoEk9Ek10 = ref(false);
    const subiendoXlsxEk9Ek10 = ref(false);
    const guardandoEk9Ek10 = ref(false);
    const errorEk9Ek10 = ref('');
    const mensajeEk9Ek10 = ref('');

    // Navegación y filtros
    const ek9Ek10TabActiva = ref('ORDENES'); // 'ORDENES' | 'DETALLE'
    const ek9Ek10MostrarGuia = ref(false);
    const ek9Ek10OrdenSeleccionadaNum = ref(null);
    const ek9Ek10DragOver = ref(false);

    const ek9Ek10FiltroTexto = ref('');
    const ek9Ek10FiltroEstado = ref('TODOS');
    const ek9Ek10OcultarCeros = ref(true);
    const ek9Ek10SoloAditivas = ref(false);

    // Filtros específicos de pestaña Detalle
    const ek9Ek10DetalleFiltroTexto = ref('');
    const ek9Ek10DetalleFiltroTipo = ref('TODOS');

    // Consultas de presupuesto por partida de insumo (key: item.id)
    const consultasPresupuestoEk9Ek10 = ref({});

    // Catálogo local y sincronización de Proveedores EK10 (EK-PROV-...)
    const proveedoresCatalogoEstado = ref({ total: 0, actualizado: '' });
    const sincronizandoProveedoresEk9Ek10 = ref(false);

    // Integración con Puffy Web para generar y fijar Requisición EK10 (key: orden.NUMERO)
    const puffyEstadoPorOrden = ref({});
    const editandoOcManual = ref({});
    const validacionOcPorOrden = ref({});

    const mostrarToastEk9Ek10 = (msg) => {
      mensajeEk9Ek10.value = msg;
      setTimeout(() => {
        if (mensajeEk9Ek10.value === msg) mensajeEk9Ek10.value = '';
      }, 2800);
    };

    const seleccionarOrdenInicial = () => {
      if (ek9Ek10Ordenes.value.length === 0) {
        ek9Ek10OrdenSeleccionadaNum.value = null;
        return;
      }
      const prioritaria = ek9Ek10Ordenes.value.find(
        o => o.ESTADO === 'OC INCOMPLETA' || o.ESTADO === 'REQUISICION INCOMPLETA' || o.ESTADO === 'SIN ORDEN DE COMPRA'
      );
      ek9Ek10OrdenSeleccionadaNum.value = prioritaria ? prioritaria.NUMERO : ek9Ek10Ordenes.value[0].NUMERO;
    };

    const aplicarRespuestaSesion = (data) => {
      ek9Ek10Cargado.value = Boolean(data.cargado);
      ek9Ek10ArchivoNombre.value = data.archivo_nombre || '';
      ek9Ek10Hojas.value = data.hojas || [];
      ek9Ek10Ordenes.value = data.ordenes || [];
      ek9Ek10Detalle.value = data.detalle || [];
      if (ek9Ek10Cargado.value) {
        seleccionarOrdenInicial();
      } else {
        ek9Ek10OrdenSeleccionadaNum.value = null;
      }
    };

    const cargarEstadoProveedoresEk9Ek10 = async () => {
      try {
        const res = await fetch('/api/ek9-ek10/proveedores/estado');
        const data = await res.json();
        if (res.ok && data.ok) {
          proveedoresCatalogoEstado.value = {
            total: data.total || 0,
            actualizado: data.actualizado || ''
          };
        }
      } catch (_) {}
    };

    const sincronizarProveedoresEk9Ek10 = async () => {
      sincronizandoProveedoresEk9Ek10.value = true;
      errorEk9Ek10.value = '';
      try {
        const res = await fetch('/api/ek9-ek10/proveedores/sincronizar', { method: 'POST' });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al sincronizar proveedores EK10');
        }
        proveedoresCatalogoEstado.value = {
          total: data.total || 0,
          actualizado: data.actualizado || ''
        };
        if (ek9Ek10Cargado.value) {
          await cargarEstadoEk9Ek10();
        }
        mostrarToastEk9Ek10(
          `Catálogo EK10 actualizado (${data.total} proveedores · ${data.ordenes_actualizadas || 0} órdenes completadas)`
        );
      } catch (err) {
        errorEk9Ek10.value = err.message || 'No se pudo sincronizar proveedores EK10';
      } finally {
        sincronizandoProveedoresEk9Ek10.value = false;
      }
    };

    const cargarEstadoEk9Ek10 = async () => {
      cargandoEk9Ek10.value = true;
      errorEk9Ek10.value = '';
      cargarEstadoProveedoresEk9Ek10();
      try {
        const res = await fetch('/api/ek9-ek10/estado');
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al consultar estado de EK9 - EK10');
        }
        aplicarRespuestaSesion(data);
      } catch (err) {
        errorEk9Ek10.value = err.message || 'No se pudo conectar con /api/ek9-ek10/estado';
      } finally {
        cargandoEk9Ek10.value = false;
      }
    };

    const abrirSelectorXlsxEk9Ek10 = () => {
      const input = document.getElementById('ek9Ek10FileInput');
      if (input) {
        input.value = '';
        input.click();
      }
    };

    const subirXlsxEk9Ek10 = async (eventOrFile) => {
      let file = null;
      if (eventOrFile && eventOrFile.target && eventOrFile.target.files) {
        file = eventOrFile.target.files[0];
      } else if (eventOrFile instanceof File) {
        file = eventOrFile;
      }
      if (!file) return;

      subiendoXlsxEk9Ek10.value = true;
      errorEk9Ek10.value = '';
      try {
        const formData = new FormData();
        formData.append('archivo', file);

        const res = await fetch('/api/ek9-ek10/cargar-xlsx', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al procesar el archivo XLSX');
        }
        ek9Ek10TabActiva.value = 'ORDENES';
        ek9Ek10FiltroEstado.value = 'TODOS';
        ek9Ek10FiltroTexto.value = '';
        ek9Ek10DetalleFiltroTexto.value = '';
        ek9Ek10DetalleFiltroTipo.value = 'TODOS';
        consultasPresupuestoEk9Ek10.value = {};
        puffyEstadoPorOrden.value = {};
        validacionOcPorOrden.value = {};
        validacionOcPorOrden.value = {};
        aplicarRespuestaSesion(data);
        mostrarToastEk9Ek10(`Archivo "${data.archivo_nombre}" cargado (${data.ordenes.length} órdenes)`);
      } catch (err) {
        errorEk9Ek10.value = err.message || 'No se pudo cargar el archivo XLSX';
      } finally {
        subiendoXlsxEk9Ek10.value = false;
        ek9Ek10DragOver.value = false;
        const input = document.getElementById('ek9Ek10FileInput');
        if (input) input.value = '';
      }
    };

    const onDropXlsxEk9Ek10 = (e) => {
      ek9Ek10DragOver.value = false;
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        subirXlsxEk9Ek10(files[0]);
      }
    };

    const limpiarEk9Ek10 = async () => {
      cargandoEk9Ek10.value = true;
      errorEk9Ek10.value = '';
      try {
        const res = await fetch('/api/ek9-ek10/limpiar', { method: 'POST' });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al limpiar vista EK9 - EK10');
        }
        aplicarRespuestaSesion(data);
        ek9Ek10FiltroTexto.value = '';
        ek9Ek10FiltroEstado.value = 'TODOS';
        ek9Ek10DetalleFiltroTexto.value = '';
        ek9Ek10DetalleFiltroTipo.value = 'TODOS';
        ek9Ek10MostrarGuia.value = false;
        consultasPresupuestoEk9Ek10.value = {};
        puffyEstadoPorOrden.value = {};
        validacionOcPorOrden.value = {};
        const input = document.getElementById('ek9Ek10FileInput');
        if (input) input.value = '';
        mostrarToastEk9Ek10('Vista limpia y lista para cargar otro XLSX');
      } catch (err) {
        errorEk9Ek10.value = err.message || 'No se pudo limpiar la vista';
      } finally {
        cargandoEk9Ek10.value = false;
      }
    };

    const guardarOrdenEk9Ek10 = async (orden, campos) => {
      guardandoEk9Ek10.value = true;
      try {
        const res = await fetch(`/api/ek9-ek10/ordenes/${orden.NUMERO}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(campos)
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.detail || 'Error al guardar orden');
        Object.assign(orden, data.orden);
        const syncKeys = ['ESTADO', 'REQUISICION_EK10', 'COMPLEMENTO', 'ORDEN_COMPRA_EK10', 'VERIFICADO_ARYVE'];
        ek9Ek10Detalle.value.forEach(d => {
          if (d.NUMERO === orden.NUMERO) {
            syncKeys.forEach(k => {
              if (k in campos) d[k] = data.orden[k];
            });
          }
        });
        mostrarToastEk9Ek10(`Orden #${orden.NUMERO} guardada`);
      } catch (err) {
        errorEk9Ek10.value = err.message;
      } finally {
        guardandoEk9Ek10.value = false;
      }
    };

    const toggleOrdenListaEk9Ek10 = async (orden) => {
      await guardarOrdenEk9Ek10(orden, { marcado_listo: !orden.marcado_listo });
    };

    const guardarDetalleEk9Ek10 = async (item, campos) => {
      guardandoEk9Ek10.value = true;
      try {
        const res = await fetch(`/api/ek9-ek10/detalle/${item.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(campos)
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.detail || 'Error al guardar partida');
        Object.assign(item, data.detalle);
        mostrarToastEk9Ek10(`Partida ${item.INSUMO || item.id} (Ord #${item.NUMERO}) guardada`);
      } catch (err) {
        errorEk9Ek10.value = err.message;
      } finally {
        guardandoEk9Ek10.value = false;
      }
    };

    const toggleDetalleListoEk9Ek10 = async (item) => {
      await guardarDetalleEk9Ek10(item, { marcado_listo: !item.marcado_listo });
    };

    const consultarPresupuestoInsumoEk9Ek10 = async (item, forzar = false) => {
      if (!item || !item.INSUMO) return;
      const key = item.id;
      const actual = consultasPresupuestoEk9Ek10.value[key];
      if (!forzar && actual && actual.abierto && actual.data) {
        actual.abierto = false;
        return;
      }

      const obra = (item.CC || (ordenSeleccionadaEk9Ek10.value && ordenSeleccionadaEk9Ek10.value.CC) || 'EY0').trim();
      const insumo = String(item.INSUMO).replace(/\.0+$/, '').trim();
      const cantidad = Number(item.CANTIDAD) || 0;

      consultasPresupuestoEk9Ek10.value[key] = {
        cargando: true,
        abierto: true,
        error: '',
        data: actual ? actual.data : null
      };

      try {
        const params = new URLSearchParams({
          obra,
          insumo,
          cantidad: String(cantidad),
          forzar: forzar ? 'true' : 'false'
        });
        const res = await fetch(`/api/ek9-ek10/consultar-presupuesto?${params.toString()}`);
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al consultar presupuesto en Centro de Presupuestos');
        }
        consultasPresupuestoEk9Ek10.value[key] = {
          cargando: false,
          abierto: true,
          error: '',
          data
        };
      } catch (err) {
        consultasPresupuestoEk9Ek10.value[key] = {
          cargando: false,
          abierto: true,
          error: err.message || 'No se pudo consultar el presupuesto',
          data: null
        };
      }
    };

    const cerrarConsultaPresupuestoEk9Ek10 = (item) => {
      if (item && consultasPresupuestoEk9Ek10.value[item.id]) {
        consultasPresupuestoEk9Ek10.value[item.id].abierto = false;
      }
    };

    const seleccionarPartidaInsumoEk9Ek10 = async (item, partida) => {
      if (!item || !partida) return;
      const campos = {
        partida_seleccionada: partida.partida_codigo || '',
        partida_seleccionada_nombre: partida.partida_nombre || '',
        partida_seleccionada_por_req: Number(partida.por_requisitar) || 0
      };
      Object.assign(item, campos);
      if (consultasPresupuestoEk9Ek10.value[item.id]) {
        consultasPresupuestoEk9Ek10.value[item.id].abierto = false;
      }
      await guardarDetalleEk9Ek10(item, campos);
    };

    const quitarPartidaInsumoEk9Ek10 = async (item) => {
      if (!item) return;
      const campos = {
        partida_seleccionada: '',
        partida_seleccionada_nombre: '',
        partida_seleccionada_por_req: null
      };
      Object.assign(item, campos);
      await guardarDetalleEk9Ek10(item, campos);
    };

    const resumenPartidasOrdenEk9Ek10 = computed(() => {
      const items = detalleOrdenSeleccionadaEk9Ek10.value || [];
      const conteo = {};
      for (const d of items) {
        if (d.partida_seleccionada) {
          conteo[d.partida_seleccionada] = (conteo[d.partida_seleccionada] || 0) + 1;
        }
      }
      return Object.entries(conteo).map(([codigo, cantidad]) => ({ codigo, cantidad }));
    });

    const prepararRequiConPuffyEk9Ek10 = async (orden) => {
      if (!orden) return;
      const itemsOrden = detallePorNumeroEk9Ek10.value[orden.NUMERO] || [];
      const checkeados = itemsOrden.filter(d => d.marcado_listo);

      if (checkeados.length === 0) {
        errorEk9Ek10.value = 'Primero marca con el check (✓) los insumos que deseas enviar a Puffy.';
        return;
      }

      const payloadItems = checkeados.map(d => {
        const cant = Number(d.FALTA_EN_ARYVE) > 0 ? Number(d.FALTA_EN_ARYVE) : (Number(d.CANTIDAD) || 0);
        let partida = (d.partida_seleccionada || '').trim();
        if (!partida && d.ESTATUS_FALTANTE) {
          const m = String(d.ESTATUS_FALTANTE).match(/(\d+(?:\.\d+)+)/);
          if (m) partida = m[1];
        }
        return {
          insumo: String(d.INSUMO || '').replace(/\.0+$/, '').trim(),
          cantidad: cant,
          partida
        };
      });

      puffyEstadoPorOrden.value[orden.NUMERO] = {
        preparando: true,
        confirmando: false,
        abierto: true,
        error: '',
        respuesta: '',
        accion_id: null,
        folio_tentativo: ''
      };
      errorEk9Ek10.value = '';

      try {
        const res = await fetch('/api/ek9-ek10/puffy/preparar-requisicion', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            numero: orden.NUMERO,
            obra: orden.CC || 'EY0',
            items: payloadItems
          })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al preparar requisición con Puffy');
        }
        puffyEstadoPorOrden.value[orden.NUMERO] = {
          preparando: false,
          confirmando: false,
          abierto: true,
          error: '',
          respuesta: data.respuesta || '',
          accion_id: data.accion_id || null,
          folio_tentativo: data.folio_tentativo || ''
        };
      } catch (err) {
        puffyEstadoPorOrden.value[orden.NUMERO] = {
          preparando: false,
          confirmando: false,
          abierto: true,
          error: err.message || 'No se pudo conectar con Puffy',
          respuesta: '',
          accion_id: null,
          folio_tentativo: ''
        };
      }
    };

    const confirmarRequiPuffyEk9Ek10 = async (orden) => {
      if (!orden) return;
      const st = puffyEstadoPorOrden.value[orden.NUMERO];
      if (!st || !st.accion_id) return;

      st.confirmando = true;
      st.error = '';
      errorEk9Ek10.value = '';

      try {
        const res = await fetch('/api/ek9-ek10/puffy/confirmar-requisicion', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            numero: orden.NUMERO,
            cc: orden.CC || 'EY0',
            accion_id: st.accion_id,
            folio_tentativo: st.folio_tentativo || ''
          })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Puffy no pudo confirmar la requisición');
        }
        if (data.folio) {
          orden.REQUISICION_EK10 = data.folio;
          orden.requi_fija_puffy = true;
          ek9Ek10Detalle.value.forEach(d => {
            if (d.NUMERO === orden.NUMERO) d.REQUISICION_EK10 = data.folio;
          });
        }
        st.confirmando = false;
        st.abierto = false;
        st.accion_id = null;
        mostrarToastEk9Ek10(`Requisición ${data.folio || ''} confirmada y fijada en Orden #${orden.NUMERO}`);
      } catch (err) {
        st.confirmando = false;
        st.error = err.message || 'Error al confirmar en Puffy';
      }
    };

    const cerrarPuffyOrdenEk9Ek10 = (orden) => {
      if (orden && puffyEstadoPorOrden.value[orden.NUMERO]) {
        puffyEstadoPorOrden.value[orden.NUMERO].abierto = false;
      }
    };

    const guardarOcManualEk9Ek10 = async (orden) => {
      if (!orden) return;
      editandoOcManual.value[orden.NUMERO] = false;
      await guardarOrdenEk9Ek10(orden, { ORDEN_COMPRA_EK10: (orden.ORDEN_COMPRA_EK10 || '').trim() });
    };

    const activarEdicionOcEk9Ek10 = (orden) => {
      if (!orden) return;
      editandoOcManual.value[orden.NUMERO] = true;
    };

    const validarOcEnkontrolEk9Ek10 = async (orden) => {
      if (!orden || !orden.ORDEN_COMPRA_EK10) return;
      const actual = validacionOcPorOrden.value[orden.NUMERO];
      if (actual && actual.abierto && actual.data && !actual.cargando) {
        actual.abierto = false;
        return;
      }

      validacionOcPorOrden.value[orden.NUMERO] = {
        cargando: true,
        abierto: true,
        error: '',
        data: null
      };

      try {
        const res = await fetch(`/api/ek9-ek10/validar-oc/${orden.NUMERO}`);
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al validar OC en Enkontrol');
        }
        validacionOcPorOrden.value[orden.NUMERO] = {
          cargando: false,
          abierto: true,
          error: '',
          data
        };
      } catch (err) {
        validacionOcPorOrden.value[orden.NUMERO] = {
          cargando: false,
          abierto: true,
          error: err.message || 'No se pudo validar la OC en Enkontrol',
          data: null
        };
      }
    };

    const cerrarValidacionOcEk9Ek10 = (orden) => {
      if (orden && validacionOcPorOrden.value[orden.NUMERO]) {
        validacionOcPorOrden.value[orden.NUMERO].abierto = false;
      }
    };

    const detallePorNumeroEk9Ek10 = computed(() => {
      const map = {};
      for (const d of ek9Ek10Detalle.value) {
        if (!map[d.NUMERO]) map[d.NUMERO] = [];
        map[d.NUMERO].push(d);
      }
      return map;
    });

    const metricasEk9Ek10 = computed(() => {
      const ords = ek9Ek10Ordenes.value;
      const total = ords.length;
      const completas = ords.filter(o => o.ESTADO === 'COMPLETA').length;
      const sinReq = ords.filter(o => o.ESTADO === 'SIN REQUISICION').length;
      const sinReqCero = ords.filter(o => o.ESTADO === 'SIN REQUISICION' && Number(o.TOTAL) === 0).length;
      const ocInc = ords.filter(o => o.ESTADO === 'OC INCOMPLETA').length;
      const reqInc = ords.filter(o => o.ESTADO === 'REQUISICION INCOMPLETA').length;
      const sinOc = ords.filter(o => o.ESTADO === 'SIN ORDEN DE COMPRA').length;
      const marcadas = ords.filter(o => o.marcado_listo).length;
      const porHacer = ords.filter(o => o.ESTADO !== 'COMPLETA' && Number(o.TOTAL) > 0).length;
      const montoTotal = ords.reduce((acc, o) => acc + (Number(o.TOTAL) || 0), 0);
      const montoPendiente = ords
        .filter(o => o.ESTADO !== 'COMPLETA' && Number(o.TOTAL) > 0)
        .reduce((acc, o) => acc + (Number(o.TOTAL) || 0), 0);

      return {
        total, completas, sinReq, sinReqCero, ocInc, reqInc, sinOc, marcadas, porHacer,
        montoTotal, montoPendiente
      };
    });

    const ordenTieneAditivaEk9Ek10 = (numero) => {
      const items = detallePorNumeroEk9Ek10.value[numero] || [];
      return items.some(d => (d.ESTATUS_FALTANTE || '').trim() === 'ADITIVA' || (Number(d.ADITIVA) || 0) > 0);
    };

    const ordenesFiltradasEk9Ek10 = computed(() => {
      const q = (ek9Ek10FiltroTexto.value || '').trim().toLowerCase();
      const est = ek9Ek10FiltroEstado.value;

      return ek9Ek10Ordenes.value.filter(o => {
        if (ek9Ek10OcultarCeros.value && Number(o.TOTAL) === 0) return false;
        if (ek9Ek10SoloAditivas.value && !ordenTieneAditivaEk9Ek10(o.NUMERO)) return false;

        if (est === 'POR_HACER') {
          if (o.ESTADO === 'COMPLETA' || Number(o.TOTAL) === 0) return false;
        } else if (est === 'MARCADAS') {
          if (!o.marcado_listo) return false;
        } else if (est !== 'TODOS') {
          if (o.ESTADO !== est) return false;
        }

        if (!q) return true;
        const items = detallePorNumeroEk9Ek10.value[o.NUMERO] || [];
        const matchOrden =
          String(o.NUMERO).includes(q) ||
          (o.NOMBRE || '').toLowerCase().includes(q) ||
          (o.REQUISICION_EK10 || '').toLowerCase().includes(q) ||
          (o.ORDEN_COMPRA_EK10 || '').toLowerCase().includes(q) ||
          (o.ESTADO || '').toLowerCase().includes(q);
        if (matchOrden) return true;
        return items.some(d =>
          (d.INSUMO || '').toLowerCase().includes(q) ||
          (d.DESCRIPCION || '').toLowerCase().includes(q)
        );
      });
    });

    const ordenSeleccionadaEk9Ek10 = computed(() => {
      if (ek9Ek10OrdenSeleccionadaNum.value === null) return null;
      return ek9Ek10Ordenes.value.find(o => o.NUMERO === ek9Ek10OrdenSeleccionadaNum.value) || null;
    });

    const detalleOrdenSeleccionadaEk9Ek10 = computed(() => {
      if (ek9Ek10OrdenSeleccionadaNum.value === null) return [];
      return detallePorNumeroEk9Ek10.value[ek9Ek10OrdenSeleccionadaNum.value] || [];
    });

    const resumenMarcadoOrdenEk9Ek10 = computed(() => {
      const o = ordenSeleccionadaEk9Ek10.value;
      const items = detalleOrdenSeleccionadaEk9Ek10.value;
      if (!o) {
        return { sub: 0, iva: 0, tot: 0, finalSub: 0, finalIva: 0, finalTot: 0, cuadrado: false, countMarcadas: 0, countTotal: 0 };
      }
      const marcadas = items.filter(d => d.marcado_listo);
      const conImporte = items.filter(d => Number(d.IMPORTE) > 0);
      const todasMarcadas = conImporte.length > 0 && conImporte.every(d => d.marcado_listo);

      let sub = marcadas.reduce((acc, d) => acc + (Number(d.IMPORTE) || 0), 0);
      let iva = 0;
      let tot = 0;

      if (todasMarcadas && Number(o.SUB_TOTAL) > 0) {
        sub = Number(o.SUB_TOTAL);
        iva = Number(o.IVA);
        tot = Number(o.TOTAL);
      } else if (Number(o.SUB_TOTAL) > 0) {
        const ratioIva = Number(o.IVA) / Number(o.SUB_TOTAL);
        const ratioTot = Number(o.TOTAL) / Number(o.SUB_TOTAL);
        iva = sub * ratioIva;
        tot = sub * ratioTot;
      }

      return {
        sub,
        iva,
        tot,
        finalSub: Number(o.SUB_TOTAL) || 0,
        finalIva: Number(o.IVA) || 0,
        finalTot: Number(o.TOTAL) || 0,
        cuadrado: todasMarcadas && Number(o.TOTAL) > 0,
        countMarcadas: marcadas.length,
        countTotal: items.length
      };
    });

    const detalleFiltradoEk9Ek10 = computed(() => {
      const q = (ek9Ek10DetalleFiltroTexto.value || '').trim().toLowerCase();
      const tipo = ek9Ek10DetalleFiltroTipo.value;

      return ek9Ek10Detalle.value.filter(d => {
        if (tipo === 'ADITIVA') {
          if ((d.ESTATUS_FALTANTE || '') !== 'ADITIVA' && !(Number(d.ADITIVA) > 0)) return false;
        } else if (tipo === 'MEDIR') {
          if (!(d.ESTATUS_FALTANTE || '').startsWith('MEDIR DISPONIBLE')) return false;
        } else if (tipo === 'DIFF_PRECIO') {
          if (d.PRECIO_EK9 == null || d.PRECIO_EK10 == null || Math.abs(d.PRECIO_EK9 - d.PRECIO_EK10) <= 0.01) return false;
        } else if (tipo === 'SIN_EK10') {
          if (!(d.PRECIO_EK9 > 0 && (d.PRECIO_EK10 === null || d.PRECIO_EK10 === ''))) return false;
        } else if (tipo === 'PENDIENTES') {
          if (d.marcado_listo || d.ESTADO === 'COMPLETA' || Number(d.CANTIDAD) === 0) return false;
        }

        if (!q) return true;
        return (
          String(d.NUMERO).includes(q) ||
          (d.INSUMO || '').toLowerCase().includes(q) ||
          (d.DESCRIPCION || '').toLowerCase().includes(q) ||
          (d.ESTATUS_FALTANTE || '').toLowerCase().includes(q) ||
          (d.ESTADO || '').toLowerCase().includes(q)
        );
      });
    });

    const accionSimpleOrdenEk9Ek10 = (o) => {
      if (Number(o.TOTAL) === 0) return 'Orden en $0 en EK9 — Ignorar / confirmar cancelada';
      switch (o.ESTADO) {
        case 'COMPLETA':
          return 'Lista y comprada en EK10 — No hacer nada';
        case 'SIN ORDEN DE COMPRA':
          return `Requi ${o.REQUISICION_EK10 || ''} completa — Solo generar OC`;
        case 'REQUISICION INCOMPLETA':
          return `Medir saldo → hacer 2a requi → generar OC con ${o.REQUISICION_EK10 || '1a requi'} + complemento`;
        case 'OC INCOMPLETA':
          return `1) Quitar OC ${o.ORDEN_COMPRA_EK10 || ''} → 2) Hacer 2a requi → 3) Recomprar ambas`;
        case 'SIN REQUISICION':
          return ordenTieneAditivaEk9Ek10(o.NUMERO)
            ? 'Revisar Detalle: tiene ADITIVA / medir saldo antes de requisitar'
            : 'Revisar Detalle: medir disponible en partidas → requisitar y hacer OC';
        default:
          return o.ESTADO || '';
      }
    };

    const accionSimplePartidaEk9Ek10 = (d) => {
      if (Number(d.CANTIDAD) === 0) return 'En $0 (sin cantidad)';
      const ef = (d.ESTATUS_FALTANTE || '').trim();
      if (!ef) return 'Completa en Aryve';
      if (ef === 'ADITIVA') return 'Pedir a Presupuestos cargar ADITIVA antes de requisitar';
      if (ef.startsWith('MEDIR DISPONIBLE EN NIVELES')) {
        const niveles = ef.replace('MEDIR DISPONIBLE EN NIVELES', '').trim();
        if (Number(d.ADITIVA) > 0 && Number(d.DISPONIBLE_NIVELES) === 0) {
          return `Revisar partida(s) ${niveles} (en Excel marcó 0 libre / posible aditiva)`;
        }
        return `Medir saldo libre en partida(s) ${niveles} en Aryve`;
      }
      return ef;
    };

    const irAOrdenDesdeDetalleEk9Ek10 = (numero) => {
      ek9Ek10OrdenSeleccionadaNum.value = numero;
      ek9Ek10TabActiva.value = 'ORDENES';
      ek9Ek10OcultarCeros.value = false;
    };

    const fmtMonedaEk9Ek10 = (val) => {
      const n = Number(val);
      if (isNaN(n)) return '$0.00';
      return n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
    };

    const fmtNumEk9Ek10 = (val) => {
      if (val === null || val === undefined || val === '') return '-';
      const n = Number(val);
      if (isNaN(n)) return val;
      return n.toLocaleString('es-MX', { maximumFractionDigits: 2 });
    };

    const exportarXlsxEk9Ek10 = () => {
      window.location.href = '/api/ek9-ek10/exportar-xlsx';
    };

    const exportarCsvEk9Ek10 = (tipo) => {
      const esc = (v) => {
        const s = v === null || v === undefined ? '' : String(v);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
      };
      let headers = [];
      let rows = [];
      let filename = '';
      if (tipo === 'ORDENES') {
        headers = ['CC','NUMERO','NOMBRE','CLAVE_PROVEEDOR','SUB_TOTAL','IVA','TOTAL','REQUISICION_EK10','COMPLEMENTO','ORDEN_COMPRA_EK10','ESTADO','VERIFICADO_ARYVE','ORIGEN_REQUISICION','MARCADO_LISTO','NOTAS_USUARIO'];
        rows = ek9Ek10Ordenes.value.map(o => [
          o.CC, o.NUMERO, o.NOMBRE, o.CLAVE_PROVEEDOR || '', o.SUB_TOTAL, o.IVA, o.TOTAL,
          o.REQUISICION_EK10, o.COMPLEMENTO, o.ORDEN_COMPRA_EK10,
          o.ESTADO, o.VERIFICADO_ARYVE, o.ORIGEN_REQUISICION,
          o.marcado_listo ? 'SI' : 'NO', o.notas_usuario || ''
        ]);
        filename = 'EK9_EK10_Ordenes_Actualizado.csv';
      } else {
        headers = ['CC','NUMERO','INSUMO','DESCRIPCION','FECHA_ENTREGA','CANTIDAD','DISPONIBLE_NIVELES','ADITIVA','PRECIO_EK9','PRECIO_EK10','IMPORTE','REQUISICION_EK10','COMPLEMENTO','ORDEN_COMPRA_EK10','ESTADO','VERIFICADO_ARYVE','ORIGEN_REQUISICION','EN_ARYVE','FALTA_EN_ARYVE','ESTATUS_FALTANTE','MARCADO_LISTO','NOTAS_USUARIO'];
        rows = ek9Ek10Detalle.value.map(d => [
          d.CC, d.NUMERO, d.INSUMO, d.DESCRIPCION, d.FECHA_ENTREGA, d.CANTIDAD,
          d.DISPONIBLE_NIVELES, d.ADITIVA, d.PRECIO_EK9, d.PRECIO_EK10, d.IMPORTE,
          d.REQUISICION_EK10, d.COMPLEMENTO, d.ORDEN_COMPRA_EK10, d.ESTADO,
          d.VERIFICADO_ARYVE, d.ORIGEN_REQUISICION, d.EN_ARYVE, d.FALTA_EN_ARYVE,
          d.ESTATUS_FALTANTE, d.marcado_listo ? 'SI' : 'NO', d.notas_usuario || ''
        ]);
        filename = 'EK9_EK10_Detalle_Actualizado.csv';
      }
      const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.map(esc).join(','))].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    return {
      ek9Ek10Cargado,
      ek9Ek10ArchivoNombre,
      ek9Ek10Hojas,
      ek9Ek10Ordenes,
      ek9Ek10Detalle,
      cargandoEk9Ek10,
      subiendoXlsxEk9Ek10,
      guardandoEk9Ek10,
      errorEk9Ek10,
      mensajeEk9Ek10,
      ek9Ek10TabActiva,
      ek9Ek10MostrarGuia,
      ek9Ek10OrdenSeleccionadaNum,
      ek9Ek10DragOver,
      ek9Ek10FiltroTexto,
      ek9Ek10FiltroEstado,
      ek9Ek10OcultarCeros,
      ek9Ek10SoloAditivas,
      ek9Ek10DetalleFiltroTexto,
      ek9Ek10DetalleFiltroTipo,
      detallePorNumeroEk9Ek10,
      metricasEk9Ek10,
      ordenesFiltradasEk9Ek10,
      ordenSeleccionadaEk9Ek10,
      detalleOrdenSeleccionadaEk9Ek10,
      resumenMarcadoOrdenEk9Ek10,
      detalleFiltradoEk9Ek10,
      cargarEstadoEk9Ek10,
      abrirSelectorXlsxEk9Ek10,
      subirXlsxEk9Ek10,
      onDropXlsxEk9Ek10,
      limpiarEk9Ek10,
      guardarOrdenEk9Ek10,
      toggleOrdenListaEk9Ek10,
      guardarDetalleEk9Ek10,
      toggleDetalleListoEk9Ek10,
      accionSimpleOrdenEk9Ek10,
      accionSimplePartidaEk9Ek10,
      irAOrdenDesdeDetalleEk9Ek10,
      fmtMonedaEk9Ek10,
      fmtNumEk9Ek10,
      exportarXlsxEk9Ek10,
      exportarCsvEk9Ek10,
      consultasPresupuestoEk9Ek10,
      consultarPresupuestoInsumoEk9Ek10,
      cerrarConsultaPresupuestoEk9Ek10,
      seleccionarPartidaInsumoEk9Ek10,
      quitarPartidaInsumoEk9Ek10,
      resumenPartidasOrdenEk9Ek10,
      proveedoresCatalogoEstado,
      sincronizandoProveedoresEk9Ek10,
      sincronizarProveedoresEk9Ek10,
      puffyEstadoPorOrden,
      editandoOcManual,
      validacionOcPorOrden,
      prepararRequiConPuffyEk9Ek10,
      confirmarRequiPuffyEk9Ek10,
      cerrarPuffyOrdenEk9Ek10,
      guardarOcManualEk9Ek10,
      activarEdicionOcEk9Ek10,
      validarOcEnkontrolEk9Ek10,
      cerrarValidacionOcEk9Ek10
    };
  };
})();
