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
