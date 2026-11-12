/**
 * Módulo JavaScript Modular: Mapeo de Lotes & Centros de Costos (Enkontrol)
 * Archivo: vue/static/js/modules/mapeo.js
 */
(function() {
  window.createMapeoModule = function(Vue) {
    const { ref, computed } = Vue;

    // Métricas y estado reactivo
    const metricasMapeo = ref({
      total_lotes: 0,
      total_ccs: 0,
      fecha_sincronizacion: '-'
    });
    const catalogoCCsMapeo = ref([]);
    const lotesMapeo = ref([]);
    const totalLotesMapeoFiltrados = ref(0);
    const cargandoMapeo = ref(false);
    const sincronizandoMapeo = ref(false);

    // Filtros de búsqueda específicos
    const filtroMapeoCC = ref('');
    const filtroMapeoManzana = ref('');
    const filtroMapeoLote = ref('');
    const filtroMapeoNoInt = ref('');
    const filtroMapeoIdEK = ref('');
    const filtroMapeoBusqueda = ref('');

    // Paginación
    const paginaMapeoActual = ref(1);
    const limiteMapeo = ref(50);

    const totalPaginasMapeo = computed(() => {
      const tot = totalLotesMapeoFiltrados.value || 0;
      return Math.max(1, Math.ceil(tot / limiteMapeo.value));
    });

    const cargarResumenMapeo = async () => {
      try {
        const res = await fetch('/api/mapeo/resumen');
        if (res.ok) {
          const d = await res.json();
          if (d.ok) {
            metricasMapeo.value = {
              total_lotes: d.total_lotes || 0,
              total_ccs: d.total_ccs || 0,
              fecha_sincronizacion: d.fecha_sincronizacion || '-'
            };
            catalogoCCsMapeo.value = d.catalogo_ccs || [];
          }
        }
      } catch (e) {
        console.error('Error cargando resumen mapeo:', e);
      }
    };

    let debounceTimerMapeo = null;
    const alCambiarFiltroMapeo = () => {
      clearTimeout(debounceTimerMapeo);
      debounceTimerMapeo = setTimeout(() => {
        consultarLotesMapeo(true);
      }, 250);
    };

    const consultarLotesMapeo = async (resetPagina = false) => {
      if (resetPagina) {
        paginaMapeoActual.value = 1;
      }
      cargandoMapeo.value = true;
      try {
        const offset = (paginaMapeoActual.value - 1) * limiteMapeo.value;
        const params = new URLSearchParams({
          limite: String(limiteMapeo.value),
          offset: String(offset)
        });
        if (filtroMapeoCC.value && filtroMapeoCC.value !== 'TODOS') params.append('cc', filtroMapeoCC.value);
        if (filtroMapeoManzana.value) params.append('manzana', filtroMapeoManzana.value);
        if (filtroMapeoLote.value) params.append('lote', filtroMapeoLote.value);
        if (filtroMapeoNoInt.value) params.append('no_int', filtroMapeoNoInt.value);
        if (filtroMapeoIdEK.value) params.append('id_lote_ek', filtroMapeoIdEK.value);
        if (filtroMapeoBusqueda.value) params.append('busqueda', filtroMapeoBusqueda.value);

        const res = await fetch(`/api/mapeo/lotes?${params.toString()}`);
        if (res.ok) {
          const d = await res.json();
          if (d.ok) {
            lotesMapeo.value = d.registros || [];
            totalLotesMapeoFiltrados.value = d.total || 0;
          }
        }
      } catch (e) {
        console.error('Error consultando lotes mapeo:', e);
      } finally {
        cargandoMapeo.value = false;
      }
    };

    const limpiarFiltrosMapeo = () => {
      filtroMapeoCC.value = '';
      filtroMapeoManzana.value = '';
      filtroMapeoLote.value = '';
      filtroMapeoNoInt.value = '';
      filtroMapeoIdEK.value = '';
      filtroMapeoBusqueda.value = '';
      consultarLotesMapeo(true);
    };

    const cambiarPaginaMapeo = (pagODelta) => {
      let target = pagODelta;
      if (pagODelta === -1 || pagODelta === 1) {
        target = paginaMapeoActual.value + pagODelta;
      }
      if (target >= 1 && target <= Math.max(1, totalPaginasMapeo.value)) {
        paginaMapeoActual.value = target;
        consultarLotesMapeo(false);
      }
    };

    const seleccionarCCMapeo = (cc) => {
      filtroMapeoCC.value = cc;
      consultarLotesMapeo(true);
    };

    const sincronizarMapeoEnkontrol = async () => {
      if (sincronizandoMapeo.value) return;
      sincronizandoMapeo.value = true;
      try {
        const res = await fetch('/api/mapeo/sincronizar', { method: 'POST' });
        const d = await res.json();
        if (res.ok && d.ok) {
          alert('✅ ' + (d.mensaje || 'Sincronización completada con éxito.'));
          await cargarResumenMapeo();
          await consultarLotesMapeo(true);
        } else {
          alert('⚠️ ' + (d.detail || d.error || 'Error al sincronizar con Enkontrol.'));
        }
      } catch (e) {
        alert('Error de conexión con el servidor: ' + e.message);
      } finally {
        sincronizandoMapeo.value = false;
      }
    };

    const exportarMapeoCSV = () => {
      if (!lotesMapeo.value || lotesMapeo.value.length === 0) {
        alert('No hay registros para exportar con los filtros actuales.');
        return;
      }
      const encabezados = [
        'CC', 
        'MANZANA_EK9', 
        'LOTE_EK9', 
        'NO_INT_EK9', 
        'ID_LOTE_EK9', 
        'CLAVE_CONSECUTIVO_EK9',
        'MANZANA_EK10',
        'LOTE_EK10',
        'NO_INT_EK10',
        'ID_EK10',
        'CLAVE_CONSECUTIVO_EK10',
        'INFO_ENK_WBS',
        'CALLE', 
        'CVE_FRACC', 
        'FRACCIONAMIENTO', 
        'MODELO_VIVIENDA', 
        'ESTATUS'
      ];
      const filas = lotesMapeo.value.map(l => [
        `"${l.cc || ''}"`,
        `"${l.manzana || ''}"`,
        `"${l.lote || ''}"`,
        `"${l.no_int || ''}"`,
        l.id_lote_ek || '',
        `"${l.clave_lote || ''}"`,
        `"${l.ek10_manzana || ''}"`,
        `"${l.ek10_lote || ''}"`,
        `"${l.ek10_no_int || ''}"`,
        l.ek10_id || '',
        `"${l.ek10_clave || ''}"`,
        `"${l.ek10_info_enk || ''}"`,
        `"${(l.calle || '').replace(/"/g, '""')}"`,
        `"${l.cve_fracc || ''}"`,
        `"${(l.fraccionamiento || '').replace(/"/g, '""')}"`,
        `"${(l.modelo || '').replace(/"/g, '""')}"`,
        `"${l.estatus || ''}"`
      ]);
      const csvContent = "\uFEFF" + [encabezados.join(','), ...filas.map(f => f.join(','))].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `MAPEO_LOTES_${filtroMapeoCC.value || 'TODOS'}_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    };

    return {
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
    };
  };
})();
