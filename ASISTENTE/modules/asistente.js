/**
 * ===============================================================================
 * MÓDULO JAVASCRIPT: ASISTENTE CENTINELA TOASTIE (OMFG HELLO TOAST)
 * Ubicación: vue/static/js/modules/asistente.js
 * Soporta: Saludo ultra-ligero instantáneo, Bautizo/Nombrado en primer inicio,
 * persistencia local + SQLite, y monitoreo en tiempo real de chat y escalatorias.
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

    // Sistema de personalización y bautizo
    const nombreGuardado = localStorage.getItem('asistente_nombre_personalizado') || 'Toastie';
    const asistenteNombrePersonalizado = ref(nombreGuardado);
    const modalNombrarAsistente = ref(false);
    const inputNuevoNombreAsistente = ref(nombreGuardado === 'Toastie' ? '' : nombreGuardado);
    const sugerenciasNombres = ['Toastie', 'Pancho', 'Ary', 'VelasBot', 'Centinela'];

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
     * Abrir modal para bautizar o renombrar al asistente
     */
    const abrirRenombrarAsistente = () => {
      inputNuevoNombreAsistente.value = asistenteNombrePersonalizado.value || '';
      modalNombrarAsistente.value = true;
      descartarGloboAsistente();
      reproducirSonidoAsistente();
    };

    /**
     * Seleccionar una sugerencia rápida
     */
    const elegirSugerenciaNombre = (nom) => {
      inputNuevoNombreAsistente.value = nom;
    };

    /**
     * Guardar el nombre asignado (bautizo del asistente)
     */
    const guardarNombreAsistente = async () => {
      const nombreLimpio = (inputNuevoNombreAsistente.value || '').trim() || 'Toastie';
      asistenteNombrePersonalizado.value = nombreLimpio;
      localStorage.setItem('asistente_nombre_personalizado', nombreLimpio);
      localStorage.setItem('asistente_onboarding_completado', 'true');
      modalNombrarAsistente.value = false;

      // Notificar al backend para guardar en SQLite
      try {
        const uVal = context?.chatUsuarioActual?.value || context?.chatUsuarioActual || {};
        const uid = uVal.id || uVal.usuario_id || 'default';

        const resp = await fetch('/api/asistente/configurar-nombre', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            usuario_id: String(uid),
            nombre_asistente: nombreLimpio
          })
        });

        if (resp.ok) {
          const res = await resp.json();
          if (res.globo) {
            hablarAsistente(res.globo);
            return;
          }
        }
      } catch (e) {
        console.warn('[Asistente] Error al persistir nombre en backend:', e);
      }

      // Confirmación visual y verbal inmediata en caso de offline
      hablarAsistente({
        id: `bautizo_${Date.now()}`,
        tipo: 'bautizo',
        titulo: `🎉 ¡Mucho gusto! Soy ${nombreLimpio}`,
        texto: `¡Me encanta ese nombre! A partir de ahora seré ${nombreLimpio}. ¡Aquí estaré en la esquina cuidando tus pendientes!`,
        subtexto: 'Nombre guardado para siempre',
        hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        accion: '',
        duracion_segundos: 9
      });
    };

    /**
     * Consulta el backend para detectar si cayó un mensaje o escalatoria nueva
     */
    const verificarEventosAsistente = async () => {
      // Si el modal de bautizo está abierto, no interrumpir con otros globos
      if (modalNombrarAsistente.value) return;

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

          // Si el backend tiene un nombre configurado y localmente no teníamos uno personalizado, sincronizar
          if (data.personaje && data.personaje.nombre && data.personaje.nombre !== 'Toastie') {
            asistenteNombrePersonalizado.value = data.personaje.nombre;
            localStorage.setItem('asistente_nombre_personalizado', data.personaje.nombre);
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
    const alHacerClicEnTostada = async () => {
      asistenteAnimando.value = true;
      setTimeout(() => { asistenteAnimando.value = false; }, 600);
      reproducirSonidoAsistente();

      // Si tiene el modal de nombrar abierto, mantener foco allí
      if (modalNombrarAsistente.value) return;

      // Si ya hay un globo visible, togglear historial
      if (asistenteGloboActual.value) {
        asistenteHistorialAbierto.value = !asistenteHistorialAbierto.value;
        return;
      }

      // Obtener reacción divertida
      try {
        const uVal = context?.chatUsuarioActual?.value || context?.chatUsuarioActual || {};
        const uid = uVal.id || uVal.usuario_id || '';
        const resp = await fetch(`/api/asistente/reaccion-clic?usuario_id=${encodeURIComponent(uid)}`);
        if (resp.ok) {
          const globo = await resp.json();
          hablarAsistente(globo);
          return;
        }
      } catch (e) {}

      // Fallback local instantáneo
      const nom = asistenteNombrePersonalizado.value || 'Toastie';
      const frases = [
        `¡OMFG HELLO! Soy ${nom}. Todo tranquilo en el sistema. Te avisaré aquí mismo si entra un correo o mensaje.`,
        `¡Aquí sigo en la esquina cuidando tus pendientes! Si un compañero te escribe en el chat, te lo diré al instante.`,
        `¡Todo al 100%! Lotes sincronizados y sin alertas críticas por el momento. ¡A darle con todo!`,
        `¿Buscando algo? Recuerda que el Mapeo de Lotes y Escalatorias están disponibles con un clic en la barra flotante.`
      ];
      const frase = frases[Math.floor(Math.random() * frases.length)];

      hablarAsistente({
        id: `click_${Date.now()}`,
        tipo: 'saludo',
        titulo: `🍞 ¡Hola! Soy ${nom}`,
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
     * Inicialización del Asistente Centinela al entrar al Dashboard
     */
    const iniciarAsistenteCentinela = async () => {
      const uVal = context?.chatUsuarioActual?.value || context?.chatUsuarioActual || {};
      const uid = uVal.id || uVal.usuario_id || '';
      const primerNombre = (uVal.nombre && uVal.nombre !== 'Cargando perfil...') 
        ? uVal.nombre.split(' ')[0] 
        : 'Esteban';

      // 1. Verificar si es el primer inicio para bautizarlo
      const onboardingCompletado = localStorage.getItem('asistente_onboarding_completado') === 'true';

      if (!onboardingCompletado) {
        try {
          const resp = await fetch(`/api/asistente/estado?usuario_id=${encodeURIComponent(uid)}&nombre=${encodeURIComponent(primerNombre)}`);
          if (resp.ok) {
            const data = await resp.json();
            if (data.primer_inicio_completado) {
              // Ya estaba registrado en backend
              localStorage.setItem('asistente_onboarding_completado', 'true');
              if (data.personaje && data.personaje.nombre) {
                asistenteNombrePersonalizado.value = data.personaje.nombre;
                localStorage.setItem('asistente_nombre_personalizado', data.personaje.nombre);
              }
            } else {
              // Primera vez: mostrar modal interactivo de bienvenida y bautizo
              modalNombrarAsistente.value = true;
              reproducirSonidoAsistente();
              // Iniciar loop de monitoreo y salir del saludo automático por ahora
              iniciarLoopMonitoreo();
              return;
            }
          }
        } catch (e) {
          // En caso de fallo de red, si no está completado mostramos el modal
          modalNombrarAsistente.value = true;
          iniciarLoopMonitoreo();
          return;
        }
      }

      // 2. Si ya fue bautizado antes, saludar de inmediato (sub-milisegundo)
      try {
        const resp = await fetch(`/api/asistente/saludo?usuario_id=${encodeURIComponent(uid)}&nombre=${encodeURIComponent(primerNombre)}`);
        if (resp.ok) {
          const saludoGlobo = await resp.json();
          hablarAsistente(saludoGlobo);
        }
      } catch (e) {}

      iniciarLoopMonitoreo();
    };

    const iniciarLoopMonitoreo = () => {
      if (!asistenteLoopPoll) {
        asistenteLoopPoll = setInterval(() => {
          verificarEventosAsistente();
        }, 4500);
      }
    };

    // Inicializar de forma segura sin retrasos perceptibles
    setTimeout(() => {
      iniciarAsistenteCentinela();
    }, 1200);

    return {
      asistenteGloboActual,
      asistenteProgresoCierre,
      asistentePausado,
      asistenteAnimando,
      asistenteHistorialAbierto,
      asistenteHistorial,
      asistenteMetricas,
      asistenteSonidoHabilitado,
      asistenteNombrePersonalizado,
      modalNombrarAsistente,
      inputNuevoNombreAsistente,
      sugerenciasNombres,
      abrirRenombrarAsistente,
      elegirSugerenciaNombre,
      guardarNombreAsistente,
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
