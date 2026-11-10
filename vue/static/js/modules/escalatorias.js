/**
 * Módulo JavaScript Modular: Buscador y Gestor de Escalatoria de Precios (SOC Enkontrol)
 * Archivo: vue/static/js/modules/escalatorias.js
 * 
 * Permite buscar instantáneamente por Obra, Clave (ej. ESC-PRECIO-TAM-0002, AD - ARMEX),
 * Insumos pactados, vista dividida tipo Enkontrol SOC, y sincronizar bajo demanda con Enkontrol 10 Cloud.
 */
(function() {
  window.createEscalatoriasModule = function(Vue) {
    const { ref, computed } = Vue;

    const metricasEscalatorias = ref({
      total_escalatorias: 0,
      autorizadas: 0,
      obras_vinculadas: 0,
      ultima_sincronizacion: null,
      total_sync: '0',
      sincronizando: false
    });

    // Modo de Visualización: 'DIVIDIDA' (Insumos vs Obras como en Enkontrol SOC) o 'TABLA' (Catálogo de Claves)
    const modoVistaEscalatorias = ref('DIVIDIDA');

    const escalatoriasRegistros = ref([]);
    const totalEscalatoriasFiltradas = ref(0);
    const cargandoEscalatorias = ref(false);
    const sincronizandoEscalatorias = ref(false);

    // Datos de la Vista Dividida (Insumos por Obra)
    const insumosPorObra = ref([]);
    const arbolWbsObra = ref({});
    const totalInsumosObra = ref(0);
    const totalObrasWbs = ref(0);
    const cargandoInsumosPorObra = ref(false);

    // Filtros de Búsqueda
    const filtroEscalatoriaBusqueda = ref('');
    const filtroEscalatoriaObra = ref('');
    const filtroEscalatoriaClave = ref('');
    const filtroEscalatoriaInsumo = ref('');
    const filtroEscalatoriaEstatus = ref('TODOS');

    // Filtro interno para la columna izquierda de insumos
    const filtroInternoInsumos = ref('');
    const insumosPorObraFiltrados = computed(() => {
      let list = insumosPorObra.value || [];
      const q = filtroInternoInsumos.value.trim().toUpperCase();
      if (!q) return list;
      return list.filter(i => {
        const nom = (i.nombre || '').toUpperCase();
        const cve = (i.clave || '').toUpperCase();
        return nom.includes(q) || cve.includes(q);
      });
    });

    // Paginación
    const paginaEscalatoriasActual = ref(1);
    const limiteEscalatorias = ref(50);
    const totalPaginasEscalatorias = computed(() => {
      const tot = totalEscalatoriasFiltradas.value || 0;
      return Math.max(1, Math.ceil(tot / limiteEscalatorias.value));
    });

    // Detalle / Visor de Insumos y Obras
    const modalDetalleEscalatoriaAbierto = ref(false);
    const escalatoriaSeleccionada = ref(null);
    const cargandoDetalleEscalatoria = ref(false);
    const tabDetalleActivo = ref('INSUMOS');
    const busquedaInsumoDetalle = ref('');
    const busquedaObraDetalle = ref('');

    const insumosDetalleFiltrados = computed(() => {
      if (!escalatoriaSeleccionada.value || !escalatoriaSeleccionada.value.insumos) return [];
      const q = busquedaInsumoDetalle.value.trim().toUpperCase();
      if (!q) return escalatoriaSeleccionada.value.insumos;
      return escalatoriaSeleccionada.value.insumos.filter(i => {
        const nom = (i.nombre || '').toUpperCase();
        const cve = (i.clave || '').toUpperCase();
        return nom.includes(q) || cve.includes(q);
      });
    });

    const obrasDetalleFiltradas = computed(() => {
      if (!escalatoriaSeleccionada.value || !escalatoriaSeleccionada.value.obras) return [];
      const q = busquedaObraDetalle.value.trim().toUpperCase();
      if (!q) return escalatoriaSeleccionada.value.obras;
      return escalatoriaSeleccionada.value.obras.filter(o => {
        const obr = (o.obra || '').toUpperCase();
        const cc = (o.centro_costo || '').toUpperCase();
        const proy = (o.proyecto || '').toUpperCase();
        return obr.includes(q) || cc.includes(q) || proy.includes(q);
      });
    });

    const cargarResumenEscalatorias = async () => {
      try {
        const res = await fetch('/api/escalatorias/resumen');
        if (res.ok) {
          const data = await res.json();
          metricasEscalatorias.value = { ...metricasEscalatorias.value, ...data };
        }
      } catch (e) {
        console.warn('Error cargando métricas de escalatorias:', e);
      }
    };

    let debounceTimer = null;
    const alCambiarFiltroEscalatorias = () => {
      paginaEscalatoriasActual.value = 1;
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        consultarEscalatorias();
        consultarInsumosPorObra();
      }, 250);
    };

    // Consulta de Vista Dividida (Insumos por Obra como en Enkontrol SOC)
    const consultarInsumosPorObra = async () => {
      cargandoInsumosPorObra.value = true;
      try {
        const params = new URLSearchParams();
        if (filtroEscalatoriaObra.value.trim()) params.append('obra', filtroEscalatoriaObra.value.trim());
        if (filtroEscalatoriaInsumo.value.trim()) params.append('insumo', filtroEscalatoriaInsumo.value.trim());
        if (filtroEscalatoriaClave.value.trim()) params.append('clave', filtroEscalatoriaClave.value.trim());
        params.append('limite', '200');

        const res = await fetch(`/api/escalatorias/por-obra?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          insumosPorObra.value = data.insumos || [];
          arbolWbsObra.value = data.obras_wbs || {};
          totalInsumosObra.value = data.total_insumos || 0;
          totalObrasWbs.value = data.total_obras || 0;
        }
      } catch (e) {
        console.error('Error consultando insumos por obra:', e);
      } finally {
        cargandoInsumosPorObra.value = false;
      }
    };

    // Consultar Escalatorias (Catálogo de Claves)
    const consultarEscalatorias = async () => {
      cargandoEscalatorias.value = true;
      try {
        const offset = (paginaEscalatoriasActual.value - 1) * limiteEscalatorias.value;
        const params = new URLSearchParams();
        if (filtroEscalatoriaBusqueda.value.trim()) params.append('busqueda', filtroEscalatoriaBusqueda.value.trim());
        if (filtroEscalatoriaObra.value.trim()) params.append('obra', filtroEscalatoriaObra.value.trim());
        if (filtroEscalatoriaClave.value.trim()) params.append('clave', filtroEscalatoriaClave.value.trim());
        if (filtroEscalatoriaInsumo.value.trim()) params.append('insumo', filtroEscalatoriaInsumo.value.trim());
        if (filtroEscalatoriaEstatus.value && filtroEscalatoriaEstatus.value !== 'TODOS') {
          params.append('estatus', filtroEscalatoriaEstatus.value);
        }
        params.append('limite', limiteEscalatorias.value);
        params.append('offset', offset);

        const res = await fetch(`/api/escalatorias/buscar?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          escalatoriasRegistros.value = data.registros || [];
          totalEscalatoriasFiltradas.value = data.total || 0;
        }
      } catch (e) {
        console.error('Error consultando escalatorias:', e);
      } finally {
        cargandoEscalatorias.value = false;
      }
    };

    const limpiarFiltrosEscalatorias = () => {
      filtroEscalatoriaBusqueda.value = '';
      filtroEscalatoriaObra.value = '';
      filtroEscalatoriaClave.value = '';
      filtroEscalatoriaInsumo.value = '';
      filtroInternoInsumos.value = '';
      filtroEscalatoriaEstatus.value = 'TODOS';
      paginaEscalatoriasActual.value = 1;
      consultarEscalatorias();
      consultarInsumosPorObra();
    };

    const cambiarPaginaEscalatorias = (nuevaPag) => {
      if (nuevaPag >= 1 && nuevaPag <= totalPaginasEscalatorias.value) {
        paginaEscalatoriasActual.value = nuevaPag;
        consultarEscalatorias();
      }
    };

    const sincronizarEscalatoriasCloud = async (silencioso = false) => {
      if (sincronizandoEscalatorias.value) return;
      sincronizandoEscalatorias.value = true;
      try {
        const res = await fetch('/api/escalatorias/sincronizar', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.ok) {
          await cargarResumenEscalatorias();
          await consultarEscalatorias();
          await consultarInsumosPorObra();
          if (!silencioso) {
            alert('✅ ' + (data.mensaje || 'Escalatorias sincronizadas con éxito.'));
          }
        } else {
          if (!silencioso) {
            alert('⚠️ Aviso: ' + (data.mensaje || 'No se pudo completar la sincronización.'));
          }
        }
      } catch (e) {
        if (!silencioso) {
          alert('Error de conexión al sincronizar: ' + e.message);
        }
      } finally {
        sincronizandoEscalatorias.value = false;
      }
    };

    const abrirDetalleEscalatoria = async (item) => {
      escalatoriaSeleccionada.value = { ...item, insumos: [], obras: [] };
      modalDetalleEscalatoriaAbierto.value = true;
      cargandoDetalleEscalatoria.value = true;
      busquedaInsumoDetalle.value = '';
      busquedaObraDetalle.value = '';
      tabDetalleActivo.value = 'INSUMOS';

      try {
        const res = await fetch(`/api/escalatorias/${item.id}/detalle`);
        if (res.ok) {
          const data = await res.json();
          escalatoriaSeleccionada.value = data;
        }
      } catch (e) {
        console.error('Error cargando detalle de escalatoria:', e);
      } finally {
        cargandoDetalleEscalatoria.value = false;
      }
    };

    const cerrarDetalleEscalatoria = () => {
      modalDetalleEscalatoriaAbierto.value = false;
      escalatoriaSeleccionada.value = null;
    };

    return {
      metricasEscalatorias,
      modoVistaEscalatorias,
      escalatoriasRegistros,
      totalEscalatoriasFiltradas,
      cargandoEscalatorias,
      sincronizandoEscalatorias,
      insumosPorObra,
      arbolWbsObra,
      totalInsumosObra,
      totalObrasWbs,
      cargandoInsumosPorObra,
      filtroInternoInsumos,
      insumosPorObraFiltrados,
      filtroEscalatoriaBusqueda,
      filtroEscalatoriaObra,
      filtroEscalatoriaClave,
      filtroEscalatoriaInsumo,
      filtroEscalatoriaEstatus,
      paginaEscalatoriasActual,
      limiteEscalatorias,
      totalPaginasEscalatorias,
      modalDetalleEscalatoriaAbierto,
      escalatoriaSeleccionada,
      cargandoDetalleEscalatoria,
      tabDetalleActivo,
      busquedaInsumoDetalle,
      busquedaObraDetalle,
      insumosDetalleFiltrados,
      obrasDetalleFiltradas,
      cargarResumenEscalatorias,
      alCambiarFiltroEscalatorias,
      consultarEscalatorias,
      consultarInsumosPorObra,
      limpiarFiltrosEscalatorias,
      cambiarPaginaEscalatorias,
      sincronizarEscalatoriasCloud,
      abrirDetalleEscalatoria,
      cerrarDetalleEscalatoria
    };
  };
})();
