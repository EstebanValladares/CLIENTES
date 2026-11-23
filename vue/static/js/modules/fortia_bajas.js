/**
 * Módulo JavaScript Modular: Inteligencia de Bajas FORTIA vs Enkontrol
 * Archivo: vue/static/js/modules/fortia_bajas.js
 */
(function() {
  window.createFortiaBajasModule = function(Vue) {
    const { ref, computed, onMounted } = Vue;

    // Estado principal
    const modalBajasFortiaAbierto = ref(false);
    const cargandoCruceFortia = ref(false);
    const cruceFortia = ref(null);
    const ejecutandoBotFortia = ref(false);
    const estadoBotFortia = ref(null);
    const pestanaBajasFortia = ref('EN_RIESGO'); // EN_RIESGO | YA_INACTIVOS | TODOS
    const busquedaBajasFortia = ref('');
    const diasAtrasFortia = ref(30);
    const headlessFortia = ref(true);
    const subiendoExcelFortia = ref(false);
    const errorCruceFortia = ref('');
    let timerPollingBot = null;

    // Métricas computadas
    const totalBajasEnRiesgo = computed(() => {
      return cruceFortia.value?.total_en_riesgo || 0;
    });

    const totalBajasFortia = computed(() => {
      return cruceFortia.value?.total_bajas_fortia || 0;
    });

    const totalYaInactivos = computed(() => {
      return cruceFortia.value?.total_ya_inactivos || 0;
    });

    const totalNoEncontrados = computed(() => {
      return cruceFortia.value?.total_no_encontrados || 0;
    });

    // Lista filtrada reactiva
    const listaBajasFiltrada = computed(() => {
      if (!cruceFortia.value) return [];
      let base = [];
      if (pestanaBajasFortia.value === 'EN_RIESGO') {
        base = cruceFortia.value.en_riesgo || [];
      } else if (pestanaBajasFortia.value === 'YA_INACTIVOS') {
        base = cruceFortia.value.ya_inactivos || [];
      } else {
        // TODOS
        base = [
          ...(cruceFortia.value.en_riesgo || []),
          ...(cruceFortia.value.ya_inactivos || []),
          ...(cruceFortia.value.no_encontrados || [])
        ];
      }

      const q = busquedaBajasFortia.value.trim().toLowerCase();
      if (!q) return base;

      return base.filter(item => {
        const nomF = (item.nombre_fortia || '').toLowerCase();
        const nomE = (item.nombre_enkontrol || '').toLowerCase();
        const clave = (item.clave_trabajador || '').toLowerCase();
        const puesto = (item.puesto_fortia || item.puesto_enkontrol || '').toLowerCase();
        return nomF.includes(q) || nomE.includes(q) || clave.includes(q) || puesto.includes(q);
      });
    });

    // Cargar cruce desde el backend
    const cargarCruceFortia = async () => {
      cargandoCruceFortia.value = true;
      errorCruceFortia.value = '';
      try {
        const res = await fetch('/api/fortia/cruce');
        if (res.ok) {
          const data = await res.json();
          if (data && data.ok) {
            cruceFortia.value = data;
          } else {
            errorCruceFortia.value = data.error || 'No hay reportes de FORTIA disponibles.';
          }
        } else {
          errorCruceFortia.value = 'No se ha procesado ningún reporte de bajas de FORTIA todavía.';
        }
      } catch (err) {
        errorCruceFortia.value = 'Error al consultar cruce de bajas: ' + err.message;
      } finally {
        cargandoCruceFortia.value = false;
      }
    };

    // Consultar estado del bot de Selenium
    const consultarEstadoBotFortia = async () => {
      try {
        const res = await fetch('/api/fortia/estado-bot');
        if (res.ok) {
          const estado = await res.json();
          estadoBotFortia.value = estado;
          ejecutandoBotFortia.value = Boolean(estado.ejecutando);

          if (!estado.ejecutando && timerPollingBot) {
            clearInterval(timerPollingBot);
            timerPollingBot = null;
            if (estado.veredicto === 'EXITO') {
              await cargarCruceFortia();
            }
          }
        }
      } catch (e) {
        console.warn('Error consultando estado bot FORTIA:', e);
      }
    };

    // Iniciar consulta de bajas con Selenium
    const iniciarConsultaBotFortia = async () => {
      if (ejecutandoBotFortia.value) return;
      errorCruceFortia.value = '';
      try {
        const url = `/api/fortia/consultar-bajas?dias_atras=${diasAtrasFortia.value}&headless=${headlessFortia.value}`;
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Error al iniciar bot');
        }
        ejecutandoBotFortia.value = true;
        // Iniciar sondeo
        if (timerPollingBot) clearInterval(timerPollingBot);
        timerPollingBot = setInterval(consultarEstadoBotFortia, 2000);
        consultarEstadoBotFortia();
      } catch (err) {
        errorCruceFortia.value = err.message;
        ejecutandoBotFortia.value = false;
      }
    };

    // Subida directa de archivo Excel de Altas y Bajas
    const subirExcelBajas = async (event) => {
      const archivo = event.target.files?.[0];
      if (!archivo) return;

      subiendoExcelFortia.value = true;
      errorCruceFortia.value = '';
      const formData = new FormData();
      formData.append('archivo', archivo);

      try {
        const res = await fetch('/api/fortia/cargar-excel', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Error al procesar el archivo Excel.');
        }
        cruceFortia.value = data;
        event.target.value = ''; // Reset file input
      } catch (err) {
        errorCruceFortia.value = err.message;
      } finally {
        subiendoExcelFortia.value = false;
      }
    };

    // Reprocesar cruce con la base de usuarios actual
    const reprocesarCruceFortia = async () => {
      cargandoCruceFortia.value = true;
      errorCruceFortia.value = '';
      try {
        const res = await fetch('/api/fortia/reprocesar', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Error al recalcular el cruce.');
        }
        cruceFortia.value = data;
      } catch (err) {
        errorCruceFortia.value = err.message;
      } finally {
        cargandoCruceFortia.value = false;
      }
    };

    // Abrir y cerrar modal
    const abrirModalBajasFortia = () => {
      modalBajasFortiaAbierto.value = true;
      cargarCruceFortia();
      consultarEstadoBotFortia();
    };

    const cerrarModalBajasFortia = () => {
      modalBajasFortiaAbierto.value = false;
    };

    // Inicializar comprobación de cruce en segundo plano
    onMounted(() => {
      cargarCruceFortia();
    });

    return {
      modalBajasFortiaAbierto,
      cargandoCruceFortia,
      cruceFortia,
      ejecutandoBotFortia,
      estadoBotFortia,
      pestanaBajasFortia,
      busquedaBajasFortia,
      diasAtrasFortia,
      headlessFortia,
      subiendoExcelFortia,
      errorCruceFortia,
      totalBajasEnRiesgo,
      totalBajasFortia,
      totalYaInactivos,
      totalNoEncontrados,
      listaBajasFiltrada,
      abrirModalBajasFortia,
      cerrarModalBajasFortia,
      cargarCruceFortia,
      iniciarConsultaBotFortia,
      subirExcelBajas,
      reprocesarCruceFortia,
      consultarEstadoBotFortia
    };
  };
})();
