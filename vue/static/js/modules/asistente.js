/**
 * ===============================================================================
 * MÓDULO JAVASCRIPT: ASISTENTE CENTINELA TOASTIE (OMFG HELLO TOAST)
 * Ubicación: vue/static/js/modules/asistente.js
 * Modo: Avatar estático en esquina, Saludo flotante al cargar, y Chat interactivo.
 * ===============================================================================
 */
(function() {
  window.createAsistenteModule = function(Vue, context) {
    const { ref, nextTick } = Vue || {};
    if (!ref) {
      console.warn('[Asistente] Vue.ref no disponible');
      return {};
    }

    // Nombre personalizado del bot
    const nombreGuardado = localStorage.getItem('asistente_nombre_personalizado') || 'Toastie';
    const asistenteNombrePersonalizado = ref(nombreGuardado);

    // Estado del globo de saludo inicial
    const asistenteGloboVisible = ref(true);
    const nombreUsuarioActivo = ref('Esteban');

    // Estado de la ventana de Chat interactivo
    const chatAsistenteAbierto = ref(false);
    const conversacionChat = ref([]);
    const textoEntradaChat = ref('');
    const cargandoRespuestaChat = ref(false);

    // Preguntas sugeridas rápidas
    const sugerenciasPreguntas = ref([
      '¿Quién es Claudia Padilla?',
      '¿Cómo está la obra HFA?',
      '¿Hay escalatorias nuevas?',
      '¿Cuándo se marca en verde la clave?'
    ]);

    let audioCtx = null;
    let temporizadorSaludo = null;

    /**
     * Sintetizador de audio con Web Audio API (Bubble Pop suave)
     */
    const reproducirSonido = () => {
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;

        if (!audioCtx) audioCtx = new AudioCtx();
        if (audioCtx.state === 'suspended') audioCtx.resume();

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        const t = audioCtx.currentTime;

        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, t);
        osc.frequency.exponentialRampToValueAtTime(880, t + 0.08);

        gain.gain.setValueAtTime(0.05, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start(t);
        osc.stop(t + 0.13);
      } catch (e) {}
    };

    /**
     * Desplazar el contenedor de chat al fondo
     */
    const scrollChatAlFondo = () => {
      setTimeout(() => {
        const el = document.getElementById('chat-asistente-scroll');
        if (el) el.scrollTop = el.scrollHeight;
      }, 50);
    };

    /**
     * Obtiene el nombre del usuario logueado en el dashboard
     */
    const detectarNombreUsuario = () => {
      const uVal = context?.chatUsuarioActual?.value || context?.chatUsuarioActual || {};
      const nomCompleto = uVal.nombre || localStorage.getItem('chat_usuario_nombre') || 'Esteban';
      
      if (nomCompleto && nomCompleto !== 'Cargando perfil...') {
        const partes = nomCompleto.trim().split(' ');
        // Si tiene nombre compuesto tipo "YEUDIEL ESTEBAN", usar "Esteban" o primer nombre
        if (partes.length >= 2 && partes[0].toUpperCase() === 'YEUDIEL') {
          nombreUsuarioActivo.value = 'Esteban';
        } else {
          nombreUsuarioActivo.value = partes[0].charAt(0).toUpperCase() + partes[0].slice(1).toLowerCase();
        }
      } else {
        nombreUsuarioActivo.value = 'Esteban';
      }
    };

    /**
     * Mensaje de bienvenida inicial en el chat
     */
    const inicializarConversacionSiEstaVacia = () => {
      if (conversacionChat.value.length === 0) {
        const bot = asistenteNombrePersonalizado.value || 'Toastie';
        const hora = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        conversacionChat.value.push({
          remitente: 'bot',
          texto: `¡Hola, ${nombreUsuarioActivo.value}! 👋 Soy ${bot}.\n\n¿En qué te puedo apoyar hoy? Puedes preguntarme sobre cualquier colaborador de la empresa, obras, lotes o escalatorias de precios.`,
          hora: hora
        });
      }
    };

    /**
     * Alternar ventana de chat al dar clic a la tostada
     */
    const toggleChatAsistente = () => {
      chatAsistenteAbierto.value = !chatAsistenteAbierto.value;
      asistenteGloboVisible.value = false;
      if (temporizadorSaludo) clearTimeout(temporizadorSaludo);

      if (chatAsistenteAbierto.value) {
        reproducirSonido();
        inicializarConversacionSiEstaVacia();
        scrollChatAlFondo();
      }
    };

    /**
     * Enviar mensaje y procesar respuesta con el cerebro cognitivo
     */
    const enviarMensajeDesdeInput = async () => {
      const q = (textoEntradaChat.value || '').trim();
      if (!q || cargandoRespuestaChat.value) return;

      const horaActual = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      // 1. Agregar mensaje del usuario a la conversación
      conversacionChat.value.push({
        remitente: 'usuario',
        texto: q,
        hora: horaActual
      });

      textoEntradaChat.value = '';
      cargandoRespuestaChat.value = true;
      scrollChatAlFondo();

      try {
        const resp = await fetch('/api/asistente/preguntar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pregunta: q,
            usuario: nombreUsuarioActivo.value
          })
        });

        if (resp.ok) {
          const res = await resp.json();
          const horaResp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          conversacionChat.value.push({
            remitente: 'bot',
            texto: res.respuesta || 'Listo.',
            hora: horaResp
          });
          reproducirSonido();
        } else {
          conversacionChat.value.push({
            remitente: 'bot',
            texto: 'Lo siento, ocurrió una incidencia temporal al consultar los datos. Por favor intenta de nuevo.',
            hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          });
        }
      } catch (e) {
        conversacionChat.value.push({
          remitente: 'bot',
          texto: 'No pude conectar con el servicio local. Verifica que el servidor esté activo.',
          hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      } finally {
        cargandoRespuestaChat.value = false;
        scrollChatAlFondo();
      }
    };

    /**
     * Enviar sugerencia rápida
     */
    const enviarPreguntaSugerida = (sug) => {
      textoEntradaChat.value = sug;
      enviarMensajeDesdeInput();
    };

    /**
     * Limpiar historial de chat
     */
    const limpiarHistorialChat = () => {
      conversacionChat.value = [];
      inicializarConversacionSiEstaVacia();
    };

    // Inicialización al arrancar
    setTimeout(() => {
      detectarNombreUsuario();
      // Ocultar saludo automáticamente a los 9 segundos si no lo tocan
      temporizadorSaludo = setTimeout(() => {
        asistenteGloboVisible.value = false;
      }, 9000);
    }, 1000);

    return {
      asistenteNombrePersonalizado,
      asistenteGloboVisible,
      nombreUsuarioActivo,
      chatAsistenteAbierto,
      conversacionChat,
      textoEntradaChat,
      cargandoRespuestaChat,
      sugerenciasPreguntas,
      toggleChatAsistente,
      enviarMensajeDesdeInput,
      enviarPreguntaSugerida,
      limpiarHistorialChat
    };
  };
})();
