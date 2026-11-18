/**
 * ===============================================================================
 * MÓDULO JAVASCRIPT: ASISTENTE CENTINELA TOASTIE (OMFG HELLO TOAST)
 * Ubicación: vue/static/js/modules/asistente.js
 * ===============================================================================
 */
(function() {
  window.createAsistenteModule = function(Vue, context) {
    const { ref } = Vue || {};
    if (!ref) {
      console.warn('[Asistente] Vue.ref no disponible');
      return {};
    }

    const asistenteGloboActual = ref(null);
    const asistenteProgresoCierre = ref(100);
    const asistentePausado = ref(false);
    const asistenteAnimando = ref(false);
    const asistenteHistorialAbierto = ref(false);
    const asistenteHistorial = ref([]);
    const asistenteMetricas = ref({
      dms_no_leidos: 0,
      escalatorias_activas: 0
    });
    const asistenteSonidoHabilitado = ref(true);

    let asistenteIntervaloCierre = null;
    let asistenteLoopPoll = null;
    let audioCtx = null;

    /**
     * Sintetizador de audio con Web Audio API (Bubble Pop suave)
     */
    const reproducirSonidoAsistente = () => {
      if (!asistenteSonidoHabilitado.value) return;
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;

        if (!audioCtx) {
          audioCtx = new AudioCtx();
        }

        if (audioCtx.state === 'suspended') {
          audioCtx.resume();
        }

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        const t = audioCtx.currentTime;

        osc.type = 'sine';
        // Tono juguetón suave ascendente tipo "burbuja / blip"
        osc.frequency.setValueAtTime(440, t);
        osc.frequency.exponentialRampToValueAtTime(880, t + 0.08);

        gain.gain.setValueAtTime(0.06, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start(t);
        osc.stop(t + 0.13);
      } catch (e) {}
    };

    /**
     * Descartar globo actual
     */
    const descartarGloboAsistente = () => {
      if (asistenteIntervaloCierre) clearInterval(asistenteIntervaloCierre);
      asistenteGloboActual.value = null;
      asistenteProgresoCierre.value = 100;
    };

    /**
     * Iniciar cuenta regresiva para autocerrar
     */
    const iniciarTemporizadorCierre = (segundosTotales) => {
      if (asistenteIntervaloCierre) clearInterval(asistenteIntervaloCierre);

      const pasoMs = 100;
      const totalPasos = (segundosTotales * 1000) / pasoMs;
      let pasoActual = totalPasos;

      asistenteIntervaloCierre = setInterval(() => {
        if (!asistentePausado.value) {
          pasoActual--;
          asistenteProgresoCierre.value = Math.max(0, (pasoActual / totalPasos) * 100);

          if (pasoActual <= 0) {
            clearInterval(asistenteIntervaloCierre);
            descartarGloboAsistente();
          }
        }
      }, pasoMs);
    };

    /**
     * Hace que la tostada hable de inmediato
     */
    const hablarAsistente = (globo) => {
      if (!globo) return;

      asistenteGloboActual.value = globo;
      asistenteProgresoCierre.value = 100;
      asistentePausado.value = false;

      // Animación de bote alegre
      asistenteAnimando.value = true;
      setTimeout(() => {
        asistenteAnimando.value = false;
      }, 700);

      // Sonido
      reproducirSonidoAsistente();

      // Autocierre
      iniciarTemporizadorCierre(globo.duracion_segundos || 8);
    };

    const pausarAutoOcultarAsistente = () => {
      asistentePausado.value = true;
    };

    const reanudarAutoOcultarAsistente = () => {
      asistentePausado.value = false;
    };

    /**
     * Consulta el backend para detectar si cayó un mensaje o escalatoria nueva
     */
    const verificarEventosAsistente = async () => {
      try {
        const uVal = context?.chatUsuarioActual?.value || context?.chatUsuarioActual || {};
        const uid = uVal.id || uVal.usuario_id || '';
        const nom = uVal.nombre || '';

        const resp = await fetch(`/api/asistente/estado?usuario_id=${encodeURIComponent(uid)}&nombre=${encodeURIComponent(nom)}`);
        if (!resp.ok) return;

        const data = await resp.json();
        if (data && data.ok) {
          if (data.metricas) {
            asistenteMetricas.value = data.metricas;
          }
          if (data.historial_reciente && data.historial_reciente.length > 0) {
            asistenteHistorial.value = data.historial_reciente;
          }

          // Si el backend detectó un nuevo evento no visto, la tostada HABLA de inmediato
          if (data.nuevo_globo) {
            hablarAsistente(data.nuevo_globo);
          }
        }
      } catch (e) {}
    };

    /**
     * Clic en el avatar de la Tostada: Saludo o reporte interactivo
     */
    const alHacerClicEnTostada = () => {
      asistenteAnimando.value = true;
      setTimeout(() => { asistenteAnimando.value = false; }, 600);
      reproducirSonidoAsistente();

      if (asistenteGloboActual.value) {
        asistenteHistorialAbierto.value = !asistenteHistorialAbierto.value;
        return;
      }

      const frases = [
        "¡OMFG HELLO! Todo tranquilo en el sistema. Te avisaré aquí mismo si entra un correo o mensaje.",
        "¡Aquí sigo en la esquina cuidando tus pendientes! Si un compañero te escribe en el chat, te lo diré al instante.",
        "¡Todo al 100%! Lotes sincronizados y sin alertas críticas por el momento. ¡A darle con todo!",
        "¿Buscando algo? Recuerda que el Mapeo de Lotes y Escalatorias están disponibles con un clic en la barra flotante."
      ];
      const frase = frases[Math.floor(Math.random() * frases.length)];

      hablarAsistente({
        id: `click_${Date.now()}`,
        tipo: 'saludo',
        titulo: '🍞 ¡OMFG HELLO!',
        texto: frase,
        subtexto: 'Tu centinela personal de pantalla',
        hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        accion: '',
        duracion_segundos: 8
      });
    };

    /**
     * Ejecuta acción del globo
     */
    const ejecutarAccionAsistente = (globo) => {
      if (!globo) return;

      if (globo.accion === 'abrir_chat') {
        if (typeof context?.abrirModalChat === 'function') {
          context.abrirModalChat();
        }
      } else if (globo.accion === 'abrir_escalatorias') {
        if (typeof context?.abrirConsultaFlotante === 'function') {
          context.abrirConsultaFlotante('ESCALATORIAS');
        }
      }

      descartarGloboAsistente();
    };

    /**
     * Saludo inicial al arrancar
     */
    const iniciarAsistenteCentinela = async () => {
      try {
        const uVal = context?.chatUsuarioActual?.value || context?.chatUsuarioActual || {};
        const primerNombre = (uVal.nombre && uVal.nombre !== 'Cargando perfil...') 
          ? uVal.nombre.split(' ')[0] 
          : 'Esteban';

        const resp = await fetch(`/api/asistente/saludo?nombre=${encodeURIComponent(primerNombre)}`);
        if (resp.ok) {
          const saludoGlobo = await resp.json();
          hablarAsistente(saludoGlobo);
        }
      } catch (e) {}

      // Arrancar loop de monitoreo cada 4.5 segundos
      if (!asistenteLoopPoll) {
        asistenteLoopPoll = setInterval(() => {
          verificarEventosAsistente();
        }, 4500);
      }
    };

    // Inicializar de forma segura sin depender exclusivamente de hooks
    setTimeout(() => {
      iniciarAsistenteCentinela();
    }, 1500);

    return {
      asistenteGloboActual,
      asistenteProgresoCierre,
      asistentePausado,
      asistenteAnimando,
      asistenteHistorialAbierto,
      asistenteHistorial,
      asistenteMetricas,
      asistenteSonidoHabilitado,
      hablarAsistente,
      descartarGloboAsistente,
      pausarAutoOcultarAsistente,
      reanudarAutoOcultarAsistente,
      alHacerClicEnTostada,
      ejecutarAccionAsistente,
      reproducirSonidoAsistente
    };
  };
})();
