/**
 * Módulo JavaScript Modular: Buscador y Gestor de Escalatoria de Precios (SOC Enkontrol)
 * Archivo: vue/static/js/modules/escalatorias.js
 * 
 * Permite buscar instantáneamente por Obra, Clave (ej. ESC-PRECIO-TAM-0002, AD - ARMEX),
 * Insumos pactados, y sincronizar bajo demanda con Enkontrol 10 Cloud.
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

    const escalatoriasRegistros = ref([]);
    const totalEscalatoriasFiltradas = ref(0);
    const cargandoEscalatorias = ref(false);
    const sincronizandoEscalatorias = ref(false);

    // Filtros de Búsqueda
    const filtroEscalatoriaBusqueda = ref('');
    const filtroEscalatoriaObra = ref('');
    const filtroEscalatoriaClave = ref('');
    const filtroEscalatoriaInsumo = ref('');
    const filtroEscalatoriaEstatus = ref('TODOS');

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
    const tabDetalleActivo = ref('INSUMOS'); // 'INSUMOS' | 'OBRAS'
    const busquedaInsumoDetalle = ref('');
    const busquedaObraDetalle = ref('');

    // Insumos filtrados dentro del modal
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

    // Obras filtradas dentro del modal
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

    // Cargar Métricas y Resumen
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
      }, 250);
    };

    // Consultar Escalatorias con filtros y paginación
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
          if (data.requiere_sync && totalEscalatoriasFiltradas.value === 0) {
            // Si la base está completamente vacía, sugerir o disparar sincronización
            sincronizarEscalatoriasCloud(true);
          }
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
      filtroEscalatoriaEstatus.value = 'TODOS';
      paginaEscalatoriasActual.value = 1;
      consultarEscalatorias();
    };

    const cambiarPaginaEscalatorias = (nuevaPag) => {
      if (nuevaPag >= 1 && nuevaPag <= totalPaginasEscalatorias.value) {
        paginaEscalatoriasActual.value = nuevaPag;
        consultarEscalatorias();
      }
    };

    // Sincronizar en Vivo desde Enkontrol 10 Cloud
    const sincronizarEscalatoriasCloud = async (silencioso = false) => {
      if (sincronizandoEscalatorias.value) return;
      sincronizandoEscalatorias.value = true;
      try {
        const res = await fetch('/api/escalatorias/sincronizar', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.ok) {
          await cargarResumenEscalatorias();
          await consultarEscalatorias();
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

    // Abrir Modal de Detalle (Insumos y Obras)
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
      escalatoriasRegistros,
      totalEscalatoriasFiltradas,
      cargandoEscalatorias,
      sincronizandoEscalatorias,
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
      limpiarFiltrosEscalatorias,
      cambiarPaginaEscalatorias,
      sincronizarEscalatoriasCloud,
      abrirDetalleEscalatoria,
      cerrarDetalleEscalatoria
    };
  };
})();
