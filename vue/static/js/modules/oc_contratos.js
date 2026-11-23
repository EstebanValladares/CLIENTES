/**
 * Módulo JavaScript Modular: Trazabilidad OC, Contratos & Insumos (Enkontrol / Aryve SOC)
 * Archivo: vue/static/js/modules/oc_contratos.js
 * 
 * Permite buscar por Folio de OC, Clave de Contrato (ELEC, MYM, PLOM, etc.) o Número + Obra.
 */
(function() {
  window.createOcContratosModule = function(Vue) {
    const { ref, computed } = Vue;

    // Filtros de búsqueda
    const filtroOcFolio = ref('');
    const filtroOcClave = ref('');
    const filtroOcObra = ref('');
    const filtroOcCompania = ref('');

    // Estado de consulta y resultados
    const cargandoOcContrato = ref(false);
    const resultadoOcContrato = ref(null);
    const errorOcContrato = ref('');
    const tabActivaOc = ref('insumos'); // 'insumos' | 'deducciones' | 'coincidencias'

    // Formateadores de moneda y fecha
    const formatearMoneda = (val) => {
      const num = Number(val || 0);
      return num.toLocaleString('es-MX', {
        style: 'currency',
        currency: 'MXN',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    };

    const formatearFecha = (str) => {
      if (!str) return 'N/D';
      try {
        const d = new Date(str.replace(' ', 'T'));
        if (isNaN(d.getTime())) return str;
        return d.toLocaleDateString('es-MX', {
          day: '2-digit',
          month: 'short',
          year: 'numeric'
        });
      } catch (e) {
        return str;
      }
    };

    // Función principal de consulta
    const consultarOcContrato = async (folioDirecto = null, obraDirecta = null, claveDirecta = null) => {
      if (folioDirecto !== null) filtroOcFolio.value = folioDirecto;
      if (obraDirecta !== null) filtroOcObra.value = obraDirecta;
      if (claveDirecta !== null) filtroOcClave.value = claveDirecta;

      const folioABuscar = (filtroOcFolio.value || '').trim();
      const claveABuscar = (filtroOcClave.value || '').trim();

      if (!folioABuscar && !claveABuscar) {
        errorOcContrato.value = 'Por favor ingresa el Folio de la OC o la Clave de Contrato (ej. ELEC, MYM, PLOM).';
        return;
      }

      cargandoOcContrato.value = true;
      errorOcContrato.value = '';
      resultadoOcContrato.value = null;

      try {
        const params = new URLSearchParams();
        if (folioABuscar) params.append('folio', folioABuscar);
        if (claveABuscar) params.append('clave', claveABuscar);
        if (filtroOcObra.value.trim()) {
          params.append('obra', filtroOcObra.value.trim());
        }
        if (filtroOcCompania.value) {
          params.append('compania', filtroOcCompania.value);
        }

        const resp = await fetch(`/api/oc-contratos/consultar?${params.toString()}`);
        const data = await resp.json();

        if (data.ok) {
          resultadoOcContrato.value = data;
          tabActivaOc.value = 'insumos';
        } else {
          errorOcContrato.value = data.mensaje || 'No se encontró la Orden de Compra o Contrato especificado.';
        }
      } catch (err) {
        console.error('Error al consultar OC y Contrato:', err);
        errorOcContrato.value = 'Ocurrió un error al conectar con el servidor de Enkontrol.';
      } finally {
        cargandoOcContrato.value = false;
      }
    };

    const limpiarConsultaOc = () => {
      filtroOcFolio.value = '';
      filtroOcClave.value = '';
      filtroOcObra.value = '';
      filtroOcCompania.value = '';
      resultadoOcContrato.value = null;
      errorOcContrato.value = '';
    };

    const seleccionarCoincidencia = (coincidencia) => {
      if (coincidencia && coincidencia.folio) {
        consultarOcContrato(coincidencia.folio, coincidencia.obra);
      }
    };

    return {
      filtroOcFolio,
      filtroOcClave,
      filtroOcObra,
      filtroOcCompania,
      cargandoOcContrato,
      resultadoOcContrato,
      errorOcContrato,
      tabActivaOc,
      formatearMoneda,
      formatearFecha,
      consultarOcContrato,
      limpiarConsultaOc,
      seleccionarCoincidencia
    };
  };
})();
