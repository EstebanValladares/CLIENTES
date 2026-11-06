/**
 * Módulo JavaScript Modular: Proveedores & Contratistas (EK10 / Aryve)
 * Archivo: vue/static/js/modules/proveedores_contratistas.js
 */
(function() {
  window.createProvContraModule = function(Vue) {
    const { ref, computed } = Vue;

    // Estado reactivo principal
    const provContraRegistros = ref([]);
    const provContraMetricas = ref({});
    const provContraCargando = ref(false);
    const provContraEjecutando = ref(false);
    const provContraModoReal = ref(false);
    const provContraLector = ref('db');
    const provContraInputNumpro = ref('');
    const provContraConsultandoDb = ref(false);
    const provContraSubiendoImagen = ref(false);
    const provContraBusqueda = ref('');
    const provContraFiltro = ref('TODOS');
    const provContraSeleccionados = ref([]);
    const provContraColumnaOrden = ref('proveedor');
    const provContraOrdenAsc = ref(true);
    const provContraTerminalLogs = ref('[Sistema preparado. Ingrese un número de proveedor o arrastre una captura EK9.]');
    const provContraModalEditor = ref(false);
    const provContraRegistroEditando = ref(null);
    const provContraModalVisor = ref(false);
    const provContraImagenVisorUrl = ref('');
    let provContraIntervaloTrabajo = null;

    // Computed Properties
    const provContraEnRevision = computed(() => {
      return provContraRegistros.value.filter(r => !r.en_historial);
    });

    const provContraEnRevisionCount = computed(() => {
      return provContraEnRevision.value.length;
    });

    const provContraMarcadosProveedorCount = computed(() => {
      return provContraRegistros.value.filter(r => r.en_historial && r.quiere_proveedor && !r.id_ek10).length;
    });

    const provContraMarcadosContratistaCount = computed(() => {
      return provContraRegistros.value.filter(r => r.en_historial && r.quiere_contratista && !r.id_contratista).length;
    });

    const toggleOrdenProvContra = (col) => {
      if (provContraColumnaOrden.value === col) {
        provContraOrdenAsc.value = !provContraOrdenAsc.value;
      } else {
        provContraColumnaOrden.value = col;
        provContraOrdenAsc.value = true;
      }
    };

    const provContraFiltrados = computed(() => {
      let list = provContraRegistros.value.filter(r => r.en_historial);
      if (provContraFiltro.value === 'PENDIENTES') {
        list = list.filter(r => (!r.id_ek10 && r.quiere_proveedor) || (!r.id_contratista && r.quiere_contratista));
      } else if (provContraFiltro.value === 'MARCADOS') {
        list = list.filter(r => (r.quiere_proveedor && !r.id_ek10) || (r.quiere_contratista && !r.id_contratista));
      } else if (provContraFiltro.value === 'REGISTRADOS') {
        list = list.filter(r => Boolean(r.id_ek10 || r.id_contratista));
      }

      const q = provContraBusqueda.value.trim().toUpperCase();
      if (q) {
        list = list.filter(r => {
          const nom = (r.nombre || '').toUpperCase();
          const rfc = (r.rfc || '').toUpperCase();
          const num = String(r.proveedor || r.id || '').toUpperCase();
          const cve = (r.clave_proveedor || '').toUpperCase();
          const idek = String(r.id_ek10 || '').toUpperCase();
          const idct = String(r.id_contratista || '').toUpperCase();
          return nom.includes(q) || rfc.includes(q) || num.includes(q) || cve.includes(q) || idek.includes(q) || idct.includes(q);
        });
      }

      const col = provContraColumnaOrden.value;
      const asc = provContraOrdenAsc.value ? 1 : -1;
      return [...list].sort((a, b) => {
        let valA = a[col] ?? '';
        let valB = b[col] ?? '';
        if (col === 'proveedor') {
          return ((Number(valA) || 0) - (Number(valB) || 0)) * asc;
        }
        return String(valA).localeCompare(String(valB)) * asc;
      });
    });

    // Métodos
    const cargarProvContraRegistros = async () => {
      provContraCargando.value = true;
      try {
        const res = await fetch('/api/prov-contra/registros');
        if (res.ok) {
          const data = await res.json();
          provContraRegistros.value = data.registros || [];
          provContraMetricas.value = data.metricas || {};
        }
      } catch (e) {
        console.error('Error cargando registros de proveedores/contratistas:', e);
      } finally {
        provContraCargando.value = false;
      }
    };

    const consultarProvContraPorNumpro = async () => {
      const numeros = [...new Set((provContraInputNumpro.value.match(/\d+/g) || []))];
      if (!numeros.length) {
        alert('Escriba el número de proveedor (ej. 11569 o varios: 11569, 11570).');
        return;
      }
      provContraConsultandoDb.value = true;
      provContraInputNumpro.value = '';
      try {
        for (const num of numeros) {
          const res = await fetch('/api/prov-contra/consultar-db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ numpro: num })
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            provContraTerminalLogs.value += `\n[OK]: Proveedor #${num} consultado desde Enkontrol.`;
          } else {
            provContraTerminalLogs.value += `\n[AVISO]: Proveedor #${num} no encontrado o error: ${data.detail || 'Error'}`;
          }
        }
        await cargarProvContraRegistros();
      } catch (e) {
        alert('Error de conexión con el servidor al consultar Enkontrol: ' + e.message);
      } finally {
        provContraConsultandoDb.value = false;
      }
    };

    const manejarDropCapturaProvContra = async (e) => {
      const files = [...(e.dataTransfer.files || [])];
      for (const file of files) {
        await subirArchivoCapturaProvContra(file);
      }
    };

    const manejarSeleccionCapturaProvContra = async (e) => {
      const files = [...(e.target.files || [])];
      for (const file of files) {
        await subirArchivoCapturaProvContra(file);
      }
      e.target.value = '';
    };

    const verificarRegistroProvContra = async (r) => {
      if (!confirm(`¿Verificar en EK10 el proveedor ${r.proveedor} ${r.nombre}?\nSe busca su RFC; si ya existe se anota su ID EK10. No se crea nada.`)) return;
      provContraEjecutando.value = true;
      try {
        const res = await fetch('/api/prov-contra/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ verificar: [r.id], proveedor: [], contratista: [], guardar: false })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          alert('Error: ' + (data.detail || data.mensaje || 'Error al verificar'));
          provContraEjecutando.value = false;
          return;
        }
        provContraTerminalLogs.value = `[${new Date().toLocaleTimeString()}] Verificando proveedor #${r.proveedor} en EK10...`;
        if (provContraIntervaloTrabajo) clearInterval(provContraIntervaloTrabajo);
        provContraIntervaloTrabajo = setInterval(async () => {
          try {
            const resp = await fetch('/api/prov-contra/trabajo');
            if (resp.ok) {
              const est = await resp.json();
              provContraTerminalLogs.value = est.lineas.join('\n');
              const el = document.getElementById('terminal-prov-contra');
              if (el) el.scrollTop = el.scrollHeight;
              if (!est.activo) {
                clearInterval(provContraIntervaloTrabajo);
                provContraEjecutando.value = false;
                await cargarProvContraRegistros();
              }
            }
          } catch (e) {
            console.error('Error obteniendo estado del trabajo:', e);
          }
        }, 1200);
      } catch (e) {
        alert('Fallo de conexión al verificar: ' + e.message);
        provContraEjecutando.value = false;
      }
    };

    const ejecutarMarcadosProvContra = async () => {
      const provs = provContraRegistros.value.filter(r => r.en_historial && r.quiere_proveedor && !r.id_ek10).map(r => r.id);
      const contras = provContraRegistros.value.filter(r => r.en_historial && r.quiere_contratista && !r.id_contratista).map(r => r.id);
      if (!provs.length && !contras.length) {
        alert('No hay registros marcados en el historial. Asegúrese de marcar la casilla "Generar" de Proveedor o Contratista.');
        return;
      }
      const esReal = provContraModoReal.value;
      const texto = `${esReal ? '⚡ ALTA REAL' : '🔍 PRUEBA (no guarda)'}\n${provs.length} proveedor(es) y ${contras.length} contratista(s).\n¿Continuar con la ejecución?`;
      if (!confirm(texto)) return;

      provContraEjecutando.value = true;
      try {
        const res = await fetch('/api/prov-contra/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ proveedor: provs, contratista: contras, guardar: esReal })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          alert('Error: ' + (data.detail || data.mensaje || 'Error al iniciar'));
          provContraEjecutando.value = false;
          return;
        }
        provContraTerminalLogs.value = `[${new Date().toLocaleTimeString()}] Iniciando ejecución (${esReal ? 'REAL' : 'PRUEBA'})...`;
        if (provContraIntervaloTrabajo) clearInterval(provContraIntervaloTrabajo);
        provContraIntervaloTrabajo = setInterval(async () => {
          try {
            const resp = await fetch('/api/prov-contra/trabajo');
            if (resp.ok) {
              const est = await resp.json();
              provContraTerminalLogs.value = est.lineas.join('\n');
              const el = document.getElementById('terminal-prov-contra');
              if (el) el.scrollTop = el.scrollHeight;
              if (!est.activo) {
                clearInterval(provContraIntervaloTrabajo);
                provContraEjecutando.value = false;
                await cargarProvContraRegistros();
              }
            }
          } catch (e) {
            console.error('Error obteniendo estado del trabajo:', e);
          }
        }, 1200);
      } catch (e) {
        alert('Fallo de conexión al ejecutar: ' + e.message);
        provContraEjecutando.value = false;
      }
    };

    const subirArchivoCapturaProvContra = (file) => {
      provContraSubiendoImagen.value = true;
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const res = await fetch('/api/prov-contra/subir-captura', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              imagen_base64: reader.result,
              filename: file.name,
              lector: provContraLector.value
            })
          });
          const data = await res.json();
          if (res.ok && data.ok) {
            await cargarProvContraRegistros();
            provContraTerminalLogs.value += `\n[OK]: Captura ${file.name} procesada correctamente.`;
          } else {
            alert(data.detail || 'Error procesando la captura de imagen.');
          }
        } catch (err) {
          alert('Fallo de conexión al enviar captura al servidor.');
        } finally {
          provContraSubiendoImagen.value = false;
        }
      };
      reader.readAsDataURL(file);
    };

    const toggleCasillaRegistro = async (id, campo, valor) => {
      try {
        await fetch(`/api/prov-contra/registros/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ [campo]: valor })
        });
        const item = provContraRegistros.value.find(r => r.id === id);
        if (item) item[campo] = valor ? 1 : 0;
      } catch (e) {
        console.error('Error actualizando casilla:', e);
      }
    };

    const enviarRegistroAHistorial = async (id) => {
      try {
        const res = await fetch(`/api/prov-contra/registros/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ en_historial: 1 })
        });
        if (res.ok) {
          await cargarProvContraRegistros();
        }
      } catch (e) {
        console.error('Error enviando a historial:', e);
      }
    };

    const enviarTodosAHistorial = async () => {
      const pendientes = provContraEnRevision.value;
      for (const item of pendientes) {
        await enviarRegistroAHistorial(item.id);
      }
      await cargarProvContraRegistros();
    };

    const toggleSeleccionProvContra = (id) => {
      const idx = provContraSeleccionados.value.indexOf(id);
      if (idx > -1) {
        provContraSeleccionados.value.splice(idx, 1);
      } else {
        provContraSeleccionados.value.push(id);
      }
    };

    const toggleSeleccionarTodosProvContra = () => {
      if (provContraSeleccionados.value.length === provContraFiltrados.value.length) {
        provContraSeleccionados.value = [];
      } else {
        provContraSeleccionados.value = provContraFiltrados.value.map(r => r.id);
      }
    };

    const abrirEditorProvContra = async (item) => {
      try {
        const res = await fetch(`/api/prov-contra/registros/${item.id}`);
        if (res.ok) {
          provContraRegistroEditando.value = await res.json();
          provContraModalEditor.value = true;
        }
      } catch (e) {
        console.error('Error abriendo editor:', e);
      }
    };

    const guardarEdicionProvContra = async () => {
      if (!provContraRegistroEditando.value) return;
      try {
        const id = provContraRegistroEditando.value.id;
        const res = await fetch(`/api/prov-contra/registros/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ campos: provContraRegistroEditando.value.campos })
        });
        if (res.ok) {
          provContraModalEditor.value = false;
          await cargarProvContraRegistros();
        } else {
          const err = await res.json();
          alert(err.detail || 'Error guardando campos editados.');
        }
      } catch (e) {
        alert('Error conectando con el servidor al guardar.');
      }
    };

    const eliminarRegistroProvContra = async (id) => {
      if (!confirm('¿Deseas eliminar este registro del historial?')) return;
      try {
        const res = await fetch(`/api/prov-contra/registros/${id}`, { method: 'DELETE' });
        if (res.ok) {
          provContraSeleccionados.value = provContraSeleccionados.value.filter(i => i !== id);
          await cargarProvContraRegistros();
        }
      } catch (e) {
        console.error('Error eliminando registro:', e);
      }
    };

    const abrirVisorImagenProvContra = (id) => {
      provContraImagenVisorUrl.value = `/api/prov-contra/imagen/${id}`;
      provContraModalVisor.value = true;
    };

    const iniciarEjecucionProvContra = async (soloVerificar = false) => {
      if (provContraSeleccionados.value.length === 0) {
        alert('Seleccione al menos un registro de la tabla para procesar.');
        return;
      }

      provContraEjecutando.value = true;
      provContraTerminalLogs.value = `[Iniciando Selenium para procesar ${provContraSeleccionados.value.length} registro(s)...]`;

      try {
        const payload = {
          proveedor: soloVerificar ? [] : provContraSeleccionados.value,
          contratista: soloVerificar ? [] : provContraSeleccionados.value,
          guardar: provContraModoReal.value,
          verificar: soloVerificar ? provContraSeleccionados.value : []
        };

        const res = await fetch('/api/prov-contra/ejecutar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const err = await res.json();
          provContraTerminalLogs.value += `\n[ERROR]: ${err.detail || 'Fallo iniciando automatización.'}`;
          provContraEjecutando.value = false;
          return;
        }

        if (provContraIntervaloTrabajo) clearInterval(provContraIntervaloTrabajo);
        provContraIntervaloTrabajo = setInterval(async () => {
          try {
            const resp = await fetch('/api/prov-contra/trabajo');
            if (resp.ok) {
              const est = await resp.json();
              provContraTerminalLogs.value = est.lineas.join('\n');
              const el = document.getElementById('terminal-prov-contra');
              if (el) el.scrollTop = el.scrollHeight;

              if (!est.activo) {
                clearInterval(provContraIntervaloTrabajo);
                provContraEjecutando.value = false;
                await cargarProvContraRegistros();
              }
            }
          } catch (e) {
            console.error('Error obteniendo estado del trabajo:', e);
          }
        }, 1200);

      } catch (e) {
        provContraTerminalLogs.value += `\n[ERROR]: Fallo de conexión: ${e.message}`;
        provContraEjecutando.value = false;
      }
    };

    const limpiarTerminalProvContra = async () => {
      try {
        await fetch('/api/prov-contra/limpiar-terminal', { method: 'POST' });
        provContraTerminalLogs.value = '[Consola limpia. Sistema listo.]';
      } catch (e) {
        provContraTerminalLogs.value = '[Consola limpia.]';
      }
    };

    return {
      provContraRegistros,
      provContraMetricas,
      provContraCargando,
      provContraEjecutando,
      provContraModoReal,
      provContraLector,
      provContraInputNumpro,
      provContraConsultandoDb,
      provContraSubiendoImagen,
      provContraBusqueda,
      provContraFiltro,
      provContraSeleccionados,
      provContraColumnaOrden,
      provContraOrdenAsc,
      provContraTerminalLogs,
      provContraModalEditor,
      provContraRegistroEditando,
      provContraModalVisor,
      provContraImagenVisorUrl,
      provContraEnRevision,
      provContraEnRevisionCount,
      provContraMarcadosProveedorCount,
      provContraMarcadosContratistaCount,
      toggleOrdenProvContra,
      provContraFiltrados,
      cargarProvContraRegistros,
      consultarProvContraPorNumpro,
      manejarDropCapturaProvContra,
      manejarSeleccionCapturaProvContra,
      verificarRegistroProvContra,
      ejecutarMarcadosProvContra,
      subirArchivoCapturaProvContra,
      toggleCasillaRegistro,
      enviarRegistroAHistorial,
      enviarTodosAHistorial,
      toggleSeleccionProvContra,
      toggleSeleccionarTodosProvContra,
      abrirEditorProvContra,
      guardarEdicionProvContra,
      eliminarRegistroProvContra,
      abrirVisorImagenProvContra,
      iniciarEjecucionProvContra,
      limpiarTerminalProvContra
    };
  };
})();
