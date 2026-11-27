/**
 * Módulo JavaScript Modular: EK9 · Órdenes EY0 & Detalle
 * Archivo: vue/static/js/modules/ek9.js
 */
(function() {
  window.createEk9Module = function(Vue) {
    const { ref, computed } = Vue;

    const ek9Ordenes = ref([]);
    const ek9Detalle = ref([]);
    const cargandoEk9 = ref(false);
    const guardandoEk9 = ref(false);
    const errorEk9 = ref('');
    const mensajeEk9 = ref('');

    // Navegación y filtros
    const ek9TabActiva = ref('ORDENES'); // 'ORDENES' | 'DETALLE'
    const ek9MostrarGuia = ref(false);
    const ek9OrdenSeleccionadaNum = ref(null);

    const ek9FiltroTexto = ref('');
    const ek9FiltroEstado = ref('TODOS'); // TODOS, POR_HACER, SIN REQUISICION, OC INCOMPLETA, REQUISICION INCOMPLETA, SIN ORDEN DE COMPRA, COMPLETA, MARCADAS
    const ek9OcultarCeros = ref(true);
    const ek9SoloAditivas = ref(false);

    // Filtros específicos de pestaña Detalle
    const ek9DetalleFiltroTexto = ref('');
    const ek9DetalleFiltroTipo = ref('TODOS'); // TODOS, ADITIVA, MEDIR, DIFF_PRECIO, SIN_EK10, PENDIENTES

    const cargarEk9Ordenes = async () => {
      cargandoEk9.value = true;
      errorEk9.value = '';
      try {
        const res = await fetch('/api/ek9/ordenes');
        const data = await res.json();
        if (!res.ok || !data.ok) {
          throw new Error(data.detail || 'Error al cargar datos de EK9');
        }
        ek9Ordenes.value = data.ordenes || [];
        ek9Detalle.value = data.detalle || [];
        if (ek9OrdenSeleccionadaNum.value === null && ek9Ordenes.value.length > 0) {
          // Seleccionar por defecto la primera orden pendiente relevante (ej. 35, 28 o 20)
          const prioritaria = ek9Ordenes.value.find(o => o.ESTADO === 'OC INCOMPLETA' || o.ESTADO === 'REQUISICION INCOMPLETA' || o.ESTADO === 'SIN ORDEN DE COMPRA');
          ek9OrdenSeleccionadaNum.value = prioritaria ? prioritaria.NUMERO : ek9Ordenes.value[0].NUMERO;
        }
      } catch (err) {
        errorEk9.value = err.message || 'No se pudo conectar con /api/ek9/ordenes';
      } finally {
        cargandoEk9.value = false;
      }
    };

    const mostrarToastEk9 = (msg) => {
      mensajeEk9.value = msg;
      setTimeout(() => {
        if (mensajeEk9.value === msg) mensajeEk9.value = '';
      }, 2600);
    };

    const guardarOrdenEk9 = async (orden, campos) => {
      guardandoEk9.value = true;
      try {
        const res = await fetch(`/api/ek9/ordenes/${orden.NUMERO}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(campos)
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.detail || 'Error al guardar orden');
        Object.assign(orden, data.orden);
        // Sincronizar campos en memoria para detalle
        const syncKeys = ['ESTADO', 'REQUISICION_EK10', 'COMPLEMENTO', 'ORDEN_COMPRA_EK10', 'VERIFICADO_ARYVE'];
        ek9Detalle.value.forEach(d => {
          if (d.NUMERO === orden.NUMERO) {
            syncKeys.forEach(k => {
              if (k in campos) d[k] = data.orden[k];
            });
          }
        });
        mostrarToastEk9(`Orden #${orden.NUMERO} guardada`);
      } catch (err) {
        errorEk9.value = err.message;
      } finally {
        guardandoEk9.value = false;
      }
    };

    const toggleOrdenListaEk9 = async (orden) => {
      const nuevoValor = !orden.marcado_listo;
      await guardarOrdenEk9(orden, { marcado_listo: nuevoValor });
    };

    const guardarDetalleEk9 = async (item, campos) => {
      guardandoEk9.value = true;
      try {
        const res = await fetch(`/api/ek9/detalle/${item.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(campos)
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.detail || 'Error al guardar partida');
        Object.assign(item, data.detalle);
        mostrarToastEk9(`Partida ${item.INSUMO} (Ord #${item.NUMERO}) guardada`);
      } catch (err) {
        errorEk9.value = err.message;
      } finally {
        guardandoEk9.value = false;
      }
    };

    const toggleDetalleListoEk9 = async (item) => {
      const nuevoValor = !item.marcado_listo;
      await guardarDetalleEk9(item, { marcado_listo: nuevoValor });
    };

    // Mapa rápido de partidas por NUMERO
    const detallePorNumero = computed(() => {
      const map = {};
      for (const d of ek9Detalle.value) {
        if (!map[d.NUMERO]) map[d.NUMERO] = [];
        map[d.NUMERO].push(d);
      }
      return map;
    });

    const metricasEk9 = computed(() => {
      const ords = ek9Ordenes.value;
      const total = ords.length;
      const completas = ords.filter(o => o.ESTADO === 'COMPLETA').length;
      const sinReq = ords.filter(o => o.ESTADO === 'SIN REQUISICION').length;
      const sinReqCero = ords.filter(o => o.ESTADO === 'SIN REQUISICION' && o.TOTAL === 0).length;
      const ocInc = ords.filter(o => o.ESTADO === 'OC INCOMPLETA').length;
      const reqInc = ords.filter(o => o.ESTADO === 'REQUISICION INCOMPLETA').length;
      const sinOc = ords.filter(o => o.ESTADO === 'SIN ORDEN DE COMPRA').length;
      const marcadas = ords.filter(o => o.marcado_listo).length;
      const porHacer = ords.filter(o => o.ESTADO !== 'COMPLETA' && o.TOTAL > 0).length;
      const montoTotal = ords.reduce((acc, o) => acc + (Number(o.TOTAL) || 0), 0);
      const montoPendiente = ords
        .filter(o => o.ESTADO !== 'COMPLETA' && o.TOTAL > 0)
        .reduce((acc, o) => acc + (Number(o.TOTAL) || 0), 0);

      return {
        total, completas, sinReq, sinReqCero, ocInc, reqInc, sinOc, marcadas, porHacer,
        montoTotal, montoPendiente
      };
    });

    const ordenTieneAditiva = (numero) => {
      const items = detallePorNumero.value[numero] || [];
      return items.some(d => (d.ESTATUS_FALTANTE || '').trim() === 'ADITIVA' || (Number(d.ADITIVA) || 0) > 0);
    };

    const ordenesFiltradasEk9 = computed(() => {
      const q = (ek9FiltroTexto.value || '').trim().toLowerCase();
      const est = ek9FiltroEstado.value;

      return ek9Ordenes.value.filter(o => {
        if (ek9OcultarCeros.value && Number(o.TOTAL) === 0) return false;
        if (ek9SoloAditivas.value && !ordenTieneAditiva(o.NUMERO)) return false;

        if (est === 'POR_HACER') {
          if (o.ESTADO === 'COMPLETA' || Number(o.TOTAL) === 0) return false;
        } else if (est === 'MARCADAS') {
          if (!o.marcado_listo) return false;
        } else if (est !== 'TODOS') {
          if (o.ESTADO !== est) return false;
        }

        if (!q) return true;
        const items = detallePorNumero.value[o.NUMERO] || [];
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

    const ordenSeleccionadaEk9 = computed(() => {
      if (ek9OrdenSeleccionadaNum.value === null) return null;
      return ek9Ordenes.value.find(o => o.NUMERO === ek9OrdenSeleccionadaNum.value) || null;
    });

    const detalleOrdenSeleccionada = computed(() => {
      if (ek9OrdenSeleccionadaNum.value === null) return [];
      return detallePorNumero.value[ek9OrdenSeleccionadaNum.value] || [];
    });

    const resumenMarcadoOrden = computed(() => {
      const o = ordenSeleccionadaEk9.value;
      const items = detalleOrdenSeleccionada.value;
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

    const detalleFiltradoEk9 = computed(() => {
      const q = (ek9DetalleFiltroTexto.value || '').trim().toLowerCase();
      const tipo = ek9DetalleFiltroTipo.value;

      return ek9Detalle.value.filter(d => {
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

    // Traductor amigable de qué hacer en cada orden
    const accionSimpleOrden = (o) => {
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
          return ordenTieneAditiva(o.NUMERO)
            ? 'Revisar Detalle: tiene ADITIVA / medir saldo antes de requisitar'
            : 'Revisar Detalle: medir disponible en partidas → requisitar y hacer OC';
        default:
          return o.ESTADO || '';
      }
    };

    const accionSimplePartida = (d) => {
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

    const irAOrdenDesdeDetalle = (numero) => {
      ek9OrdenSeleccionadaNum.value = numero;
      ek9TabActiva.value = 'ORDENES';
      ek9OcultarCeros.value = false;
    };

    const fmtMonedaEk9 = (val) => {
      const n = Number(val);
      if (isNaN(n)) return '$0.00';
      return n.toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });
    };

    const fmtNumEk9 = (val) => {
      if (val === null || val === undefined || val === '') return '-';
      const n = Number(val);
      if (isNaN(n)) return val;
      return n.toLocaleString('es-MX', { maximumFractionDigits: 2 });
    };

    const exportarCsvEk9 = (tipo) => {
      const esc = (v) => {
        const s = v === null || v === undefined ? '' : String(v);
        return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
      };
      let headers = [];
      let rows = [];
      let filename = '';
      if (tipo === 'ORDENES') {
        headers = ['CC','NUMERO','NOMBRE','SUB_TOTAL','IVA','TOTAL','REQUISICION_EK10','COMPLEMENTO','ORDEN_COMPRA_EK10','ESTADO','VERIFICADO_ARYVE','ORIGEN_REQUISICION','MARCADO_LISTO','NOTAS_USUARIO'];
        rows = ek9Ordenes.value.map(o => [
          o.CC, o.NUMERO, o.NOMBRE, o.SUB_TOTAL, o.IVA, o.TOTAL,
          o.REQUISICION_EK10, o.COMPLEMENTO, o.ORDEN_COMPRA_EK10,
          o.ESTADO, o.VERIFICADO_ARYVE, o.ORIGEN_REQUISICION,
          o.marcado_listo ? 'SI' : 'NO', o.notas_usuario || ''
        ]);
        filename = 'EK9_EY0_Ordenes_Actualizado.csv';
      } else {
        headers = ['CC','NUMERO','INSUMO','DESCRIPCION','FECHA_ENTREGA','CANTIDAD','DISPONIBLE_NIVELES','ADITIVA','PRECIO_EK9','PRECIO_EK10','IMPORTE','REQUISICION_EK10','COMPLEMENTO','ORDEN_COMPRA_EK10','ESTADO','VERIFICADO_ARYVE','ORIGEN_REQUISICION','EN_ARYVE','FALTA_EN_ARYVE','ESTATUS_FALTANTE','MARCADO_LISTO','NOTAS_USUARIO'];
        rows = ek9Detalle.value.map(d => [
          d.CC, d.NUMERO, d.INSUMO, d.DESCRIPCION, d.FECHA_ENTREGA, d.CANTIDAD,
          d.DISPONIBLE_NIVELES, d.ADITIVA, d.PRECIO_EK9, d.PRECIO_EK10, d.IMPORTE,
          d.REQUISICION_EK10, d.COMPLEMENTO, d.ORDEN_COMPRA_EK10, d.ESTADO,
          d.VERIFICADO_ARYVE, d.ORIGEN_REQUISICION, d.EN_ARYVE, d.FALTA_EN_ARYVE,
          d.ESTATUS_FALTANTE, d.marcado_listo ? 'SI' : 'NO', d.notas_usuario || ''
        ]);
        filename = 'EK9_EY0_Detalle_Actualizado.csv';
      }
      const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.map(esc).join(','))].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      mostrarToastEk9(`Descargado ${filename}`);
    };

    return {
      ek9Ordenes,
      ek9Detalle,
      cargandoEk9,
      guardandoEk9,
      errorEk9,
      mensajeEk9,
      ek9TabActiva,
      ek9MostrarGuia,
      ek9OrdenSeleccionadaNum,
      ek9FiltroTexto,
      ek9FiltroEstado,
      ek9OcultarCeros,
      ek9SoloAditivas,
      ek9DetalleFiltroTexto,
      ek9DetalleFiltroTipo,
      metricasEk9,
      ordenesFiltradasEk9,
      ordenSeleccionadaEk9,
      detalleOrdenSeleccionada,
      resumenMarcadoOrden,
      detalleFiltradoEk9,
      detallePorNumero,
      cargarEk9Ordenes,
      guardarOrdenEk9,
      toggleOrdenListaEk9,
      guardarDetalleEk9,
      toggleDetalleListoEk9,
      accionSimpleOrden,
      accionSimplePartida,
      ordenTieneAditiva,
      irAOrdenDesdeDetalle,
      fmtMonedaEk9,
      fmtNumEk9,
      exportarCsvEk9
    };
  };
})();
