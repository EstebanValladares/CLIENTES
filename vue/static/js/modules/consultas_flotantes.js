/**
 * Módulo JavaScript Modular: Gestor de Consultas Flotantes Rápidas
 * Archivo: vue/static/js/modules/consultas_flotantes.js
 * 
 * Permite desplegar iconos flotantes desde el logo principal y abrir
 * ventanas flotantes de consulta (ej. MAPEO) sin abandonar la vista activa.
 */
(function() {
  window.createConsultasFlotantesModule = function(Vue, context) {
    const { ref } = Vue;

    const menuConsultasAbierto = ref(false);
    const consultaFlotanteActiva = ref(null); // 'MAPEO' o null
    const consultaMaximizada = ref(false);

    // Registro escalable de herramientas de consulta rápida
    const catalogoConsultas = ref([
      {
        id: 'MAPEO',
        nombre: 'Mapeo de Lotes & Consecutivo',
        subtitulo: 'Catálogo Maestro Enkontrol (116k+ lotes)',
        icono: 'fa-solid fa-map-location-dot',
        badge: '116k+ lotes',
        color: 'from-blue-600 via-indigo-600 to-cyan-500',
        iconoColor: 'text-cyan-400',
        bgIcono: 'bg-cyan-500/15 border-cyan-500/30',
        descripcion: 'Buscador instantáneo por Centro de Costo, Manzana, Lote, No. Interior e ID Lote EK.'
      },
      {
        id: 'ESCALATORIAS',
        nombre: 'Escalatoria de Precios (SOC)',
        subtitulo: 'Tabulador de Precios e Insumos por Obra',
        icono: 'fa-solid fa-arrow-trend-up',
        badge: '86 claves',
        color: 'from-amber-500 via-amber-600 to-orange-500',
        iconoColor: 'text-amber-400',
        bgIcono: 'bg-amber-500/15 border-amber-500/30',
        descripcion: 'Búsqueda por Obra, Clave de escalatoria e insumos con sincronización en vivo de Enkontrol Cloud.'
      },
      {
        id: 'OC_CONTRATOS',
        nombre: 'OC, Contratos & Insumos',
        subtitulo: 'Trazabilidad Integral de Estimaciones y Subcontratos',
        icono: 'fa-solid fa-file-contract',
        badge: 'En vivo',
        color: 'from-emerald-500 via-teal-600 to-cyan-500',
        iconoColor: 'text-emerald-400',
        bgIcono: 'bg-emerald-500/15 border-emerald-500/30',
        descripcion: 'Consulta instantánea de Contratos, Estimaciones, Deducciones de Anticipo e Insumos por Folio de OC.'
      },
      {
        id: 'EK9',
        nombre: 'EK9 · Órdenes EY0 & Detalle',
        subtitulo: 'Migración EY0 (EK9 → EK10 / Aryve)',
        icono: 'fa-solid fa-table-list',
        badge: '82 órdenes',
        color: 'from-violet-600 via-purple-600 to-fuchsia-500',
        iconoColor: 'text-violet-400',
        bgIcono: 'bg-violet-500/15 border-violet-500/30',
        descripcion: 'Visualiza y edita las órdenes EY0 y su detalle conectado por NUMERO antes de tocar el Excel.'
      }
    ]);

    const toggleMenuConsultas = (event) => {
      if (event) {
        if (typeof event.stopPropagation === 'function') event.stopPropagation();
        if (typeof event.preventDefault === 'function') event.preventDefault();
      }
      menuConsultasAbierto.value = !menuConsultasAbierto.value;
    };

    const abrirConsultaFlotante = (id) => {
      consultaFlotanteActiva.value = id;
      menuConsultasAbierto.value = false;

      // Si es MAPEO, disparar la carga de datos si aún no se han cargado
      if (id === 'MAPEO') {
        if (context && typeof context.cargarResumenMapeo === 'function') {
          context.cargarResumenMapeo();
          context.consultarLotesMapeo();
        } else if (typeof window.cargarResumenMapeoGlobal === 'function') {
          window.cargarResumenMapeoGlobal();
        }
      } else if (id === 'ESCALATORIAS') {
        if (context && typeof context.cargarResumenEscalatorias === 'function') {
          context.cargarResumenEscalatorias();
          context.consultarEscalatorias();
        }
      } else if (id === 'EK9') {
        if (context && typeof context.cargarEk9Ordenes === 'function') {
          context.cargarEk9Ordenes();
        }
      }
    };

    const cerrarConsultaFlotante = () => {
      consultaFlotanteActiva.value = null;
      consultaMaximizada.value = false;
    };

    const toggleMaximizarConsulta = () => {
      consultaMaximizada.value = !consultaMaximizada.value;
    };

    // Cerrar menú únicamente con clic afuera del botón o del dock flotante
    document.addEventListener('click', (e) => {
      if (!menuConsultasAbierto.value) return;
      const target = e.target;
      if (target && target.closest && target.closest('.launcher-consultas-wrapper')) {
        return;
      }
      menuConsultasAbierto.value = false;
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (consultaFlotanteActiva.value) {
          cerrarConsultaFlotante();
        } else if (menuConsultasAbierto.value) {
          menuConsultasAbierto.value = false;
        }
      }
    });

    return {
      menuConsultasAbierto,
      consultaFlotanteActiva,
      consultaMaximizada,
      catalogoConsultas,
      toggleMenuConsultas,
      abrirConsultaFlotante,
      cerrarConsultaFlotante,
      toggleMaximizarConsulta
    };
  };
})();
