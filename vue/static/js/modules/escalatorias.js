/**
 * Módulo JavaScript Modular: Buscador y Gestor de Escalatoria de Precios (SOC Enkontrol)
 * Archivo: vue/static/js/modules/escalatorias.js
 * 
 * Permite buscar instantáneamente en una SOLA PANTALLA UNIFICADA por:
 * - Obra / Proyecto (ej. KB1, AR0, VISTA LAGUNA)
 * - Clave de Escalatoria (ej. ESC-PRECIO-TAM-0002, AD VARILLA BIENESTAR)
 * - Insumo / Material (ej. 1040025, VARILLA, ARMEX)
 * - Búsqueda Libre
 * 
 * Al hacer clic en cualquier Clave/Fila, se despliega inline el desglose
 * exacto de insumos autorizados para esa obra con sus precios pactados ($).
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

    // Estado del Acordeón Inline (Despliegue de Insumos por Clave & Obra)
    const claveExpandidaId = ref(null);
    const insumosClaveSeleccionada = ref([]);
    const cargandoInsumosClave = ref(false);
    const infoClaveExpandida = ref(null);
    const filtroInsumosExpandidos = ref('');
    const verTodosInsumosClave = ref(false);

    // Insumos filtrados internamente en el acordeón expandido
    const insumosExpandidosFiltrados = computed(() => {
      let list = insumosClaveSeleccionada.value || [];
      const q = filtroInsumosExpandidos.value.trim().toUpperCase();
      if (!q) return list;
      return list.filter(i => {
        const nom = (i.nombre || '').toUpperCase();
        const cve = (i.clave || '').toUpperCase();
        const obr = (i.obra_nombre || i.obra_clave || '').toUpperCase();
        return nom.includes(q) || cve.includes(q) || obr.includes(q);
      });
    });

    // Paginación
    const paginaEscalatoriasActual = ref(1);
    const limiteEscalatorias = ref(50);
    const totalPaginasEscalatorias = computed(() => {
      const tot = totalEscalatoriasFiltradas.value || 0;
      return Math.max(1, Math.ceil(tot / limiteEscalatorias.value));
    });

    // Modal secundario de Ficha Completa
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

    const formatearPrecio = (valor) => {
      if (valor === null || valor === undefined || valor === '' || isNaN(valor)) return '$ 0.00';
      return '$ ' + Number(valor).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    };

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
        if (claveExpandidaId.value) {
          const esc = escalatoriasRegistros.value.find(e => e.id === claveExpandidaId.value) || { id: claveExpandidaId.value };
          toggleExpandirClave(esc, true);
        }
      }, 250);
    };

    // Consultar Escalatorias (Catálogo de Claves / Folios)
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

    // Despliega o contrae el acordeón inline para ver los insumos y precios de esa clave y obra
    const toggleExpandirClave = async (esc, forceOpen = false, forzarTodos = false) => {
      if (!esc || !esc.id) return;

      if (forzarTodos) {
        verTodosInsumosClave.value = !verTodosInsumosClave.value;
      }

      if (claveExpandidaId.value === esc.id && !forceOpen && !forzarTodos) {
        claveExpandidaId.value = null;
        insumosClaveSeleccionada.value = [];
        infoClaveExpandida.value = null;
        filtroInsumosExpandidos.value = '';
        verTodosInsumosClave.value = false;
        return;
      }

      claveExpandidaId.value = esc.id;
      cargandoInsumosClave.value = true;
      filtroInsumosExpandidos.value = '';

      try {
        const params = new URLSearchParams();
        if (!verTodosInsumosClave.value) {
          if (filtroEscalatoriaObra.value.trim()) {
            params.append('obra', filtroEscalatoriaObra.value.trim());
          }
          if (filtroEscalatoriaInsumo.value.trim()) {
            params.append('insumo', filtroEscalatoriaInsumo.value.trim());
          }
        }

        const res = await fetch(`/api/escalatorias/${esc.id}/insumos-obra?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          insumosClaveSeleccionada.value = data.insumos || [];
          infoClaveExpandida.value = data;
        }
      } catch (e) {
        console.error('Error consultando insumos de la clave:', e);
      } finally {
        cargandoInsumosClave.value = false;
      }
    };

    const limpiarFiltrosEscalatorias = () => {
      filtroEscalatoriaBusqueda.value = '';
      filtroEscalatoriaObra.value = '';
      filtroEscalatoriaClave.value = '';
      filtroEscalatoriaInsumo.value = '';
      filtroEscalatoriaEstatus.value = 'TODOS';
      filtroInsumosExpandidos.value = '';
      claveExpandidaId.value = null;
      insumosClaveSeleccionada.value = [];
      infoClaveExpandida.value = null;
      verTodosInsumosClave.value = false;
      paginaEscalatoriasActual.value = 1;
      consultarEscalatorias();
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
          if (claveExpandidaId.value) {
            const esc = escalatoriasRegistros.value.find(e => e.id === claveExpandidaId.value) || { id: claveExpandidaId.value };
            toggleExpandirClave(esc, true);
          }
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
      escalatoriasRegistros,
      totalEscalatoriasFiltradas,
      cargandoEscalatorias,
      sincronizandoEscalatorias,
      filtroEscalatoriaBusqueda,
      filtroEscalatoriaObra,
      filtroEscalatoriaClave,
      filtroEscalatoriaInsumo,
      filtroEscalatoriaEstatus,
      claveExpandidaId,
      insumosClaveSeleccionada,
      cargandoInsumosClave,
      infoClaveExpandida,
      filtroInsumosExpandidos,
      insumosExpandidosFiltrados,
      verTodosInsumosClave,
      toggleExpandirClave,
      formatearPrecio,
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
