/**
 * ===============================================================================
 * MÓDULO JS: ASISTENTE CENTINELA (TOASTIE - OMFG HELLO TOAST)
 * Ubicación: vue/static/js/modules/asistente.js
 * ===============================================================================
 */

window.AsistenteModulo = {
  data() {
    return {
      asistenteGloboActual: null,
      asistenteProgresoCierre: 100,
      asistenteTimerCierre: null,
      asistenteIntervaloCierre: null,
      asistentePausado: false,
      asistenteAnimando: false,
      asistenteHistorialAbierto: false,
      asistenteHistorial: [],
      asistenteMetricas: {
        dms_no_leidos: 0,
        escalatorias_activas: 0
      },
      asistenteSonidoHabilitado: true,
      asistenteLoopPoll: null,
      asistenteAudioCtx: null
    };
  },

  mounted() {
    // Iniciar con un breve delay para que la UI termine de cargar
    setTimeout(() => {
      this.iniciarAsistenteCentinela();
    }, 1800);
  },

  beforeUnmount() {
    if (this.asistenteLoopPoll) {
      clearInterval(this.asistenteLoopPoll);
    }
  },

  methods: {
    /**
     * Inicializa el centinela, emite saludo proactivo y arranca polling de eventos.
     */
    async iniciarAsistenteCentinela() {
      // 1. Saludo proactivo inicial al abrir el Dashboard
      try {
        const nombreColaborador = (this.chatUsuarioActual && this.chatUsuarioActual.nombre && this.chatUsuarioActual.nombre !== 'Cargando perfil...') 
          ? this.chatUsuarioActual.nombre.split(' ')[0] 
          : 'Esteban';

        const resp = await fetch(`/api/asistente/saludo?nombre=${encodeURIComponent(nombreColaborador)}`);
        if (resp.ok) {
          const saludoGlobo = await resp.json();
          this.hablarAsistente(saludoGlobo);
        }
      } catch (e) {
        console.warn('[Asistente] No se pudo obtener saludo inicial:', e);
      }

      // 2. Monitoreo reactivo de eventos cada 4.5 segundos
      this.asistenteLoopPoll = setInterval(() => {
        this.verificarEventosAsistente();
      }, 4500);
    },

    /**
     * Consulta el backend para detectar si cayó un mensaje o escalatoria nueva.
     */
    async verificarEventosAsistente() {
      try {
        const uid = (this.chatUsuarioActual && this.chatUsuarioActual.usuario_id) ? this.chatUsuarioActual.usuario_id : '';
        const nom = (this.chatUsuarioActual && this.chatUsuarioActual.nombre) ? this.chatUsuarioActual.nombre : '';

        const resp = await fetch(`/api/asistente/estado?usuario_id=${uid}&nombre=${encodeURIComponent(nom)}`);
        if (!resp.ok) return;

        const data = await resp.json();
        if (data.ok) {
          if (data.metricas) {
            this.asistenteMetricas = data.metricas;
          }
          if (data.historial_reciente && data.historial_reciente.length > 0) {
            this.asistenteHistorial = data.historial_reciente;
          }

          // Si el backend detectó un nuevo evento no visto, la tostada HABLA de inmediato
          if (data.nuevo_globo) {
            this.hablarAsistente(data.nuevo_globo);
          }
        }
      } catch (e) {
        // Silencioso para no ensuciar consola
      }
    },

    /**
     * Muestra el globo de diálogo en la esquina, reproduce sonido y anima la tostada.
     */
    hablarAsistente(globo) {
      if (!globo) return;

      this.asistenteGloboActual = globo;
      this.asistenteProgresoCierre = 100;
      this.asistentePausado = false;

      // Animación de bote alegre de la tostada
      this.asistenteAnimando = true;
      setTimeout(() => {
        this.asistenteAnimando = false;
      }, 700);

      // Reproducir sonido sutil pop
      this.reproducirSonidoAsistente();

      // Iniciar cuenta regresiva para autocerrar
      this.iniciarTemporizadorCierre(globo.duracion_segundos || 8);
    },

    iniciarTemporizadorCierre(segundosTotales) {
      if (this.asistenteTimerCierre) clearTimeout(this.asistenteTimerCierre);
      if (this.asistenteIntervaloCierre) clearInterval(this.asistenteIntervaloCierre);

      const pasoMs = 100;
      const totalPasos = (segundosTotales * 1000) / pasoMs;
      let pasoActual = totalPasos;

      this.asistenteIntervaloCierre = setInterval(() => {
        if (!this.asistentePausado) {
          pasoActual--;
          this.asistenteProgresoCierre = Math.max(0, (pasoActual / totalPasos) * 100);

          if (pasoActual <= 0) {
            clearInterval(this.asistenteIntervaloCierre);
            this.descartarGloboAsistente();
          }
        }
      }, pasoMs);
    },

    pausarAutoOcultarAsistente() {
      this.asistentePausado = true;
    },

    reanudarAutoOcultarAsistente() {
      this.asistentePausado = false;
    },

    descartarGloboAsistente() {
      if (this.asistenteTimerCierre) clearTimeout(this.asistenteTimerCierre);
      if (this.asistenteIntervaloCierre) clearInterval(this.asistenteIntervaloCierre);
      this.asistenteGloboActual = null;
      this.asistenteProgresoCierre = 100;
    },

    /**
     * Clic en el avatar de la Tostada: Reacciona con alegría y da un reporte rápido.
     */
    alHacerClicEnTostada() {
      this.asistenteAnimando = true;
      setTimeout(() => { this.asistenteAnimando = false; }, 600);
      this.reproducirSonidoAsistente();

      if (this.asistenteGloboActual) {
        // Si ya está hablando, alterna el historial
        this.asistenteHistorialAbierto = !this.asistenteHistorialAbierto;
        return;
      }

      // Si no tiene nada que decir en este momento, saluda alegremente
      const frases = [
        "¡OMFG HELLO! Todo tranquilo en el sistema. Te avisaré aquí mismo si entra un correo o mensaje.",
        "¡Aquí sigo vigilando la pantalla! Si un compañero te escribe en el chat, te lo diré al instante.",
        "¡Todo al 100%! Lotes sincronizados y sin alertas críticas por el momento. ¡Buen trabajo!",
        "¿Buscando algo? Recuerda que el Mapeo de Lotes y Escalatorias están activos en la barra de consultas."
      ];
      const frase = frases[Math.floor(Math.random() * frases.length)];

      this.hablarAsistente({
        id: `click_${Date.now()}`,
        tipo: 'saludo',
        titulo: '🍞 ¡OMFG HELLO!',
        texto: frase,
        subtexto: 'Tu compañero centinela en pantalla',
        hora: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        accion: '',
        duracion_segundos: 7
      });
    },

    /**
     * Ejecuta la acción rápida asociada al globo (ej. saltar al chat o escalatorias).
     */
    ejecutarAccionAsistente(globo) {
      if (!globo) return;

      if (globo.accion === 'abrir_chat') {
        // Abrir pestaña o modal de chat si existe
        if (typeof this.abrirModalChat === 'function') {
          this.abrirModalChat();
        } else if (typeof this.seleccionarContactoChat === 'function' && globo.payload?.usuario_id) {
          this.seleccionarContactoChat({ usuario_id: globo.payload.usuario_id, nombre: globo.emisor });
        }
      } else if (globo.accion === 'abrir_escalatorias') {
        // Abrir consulta flotante de escalatorias
        if (typeof this.abrirConsultaFlotante === 'function') {
          this.abrirConsultaFlotante('ESCALATORIAS');
        }
      }

      this.descartarGloboAsistente();
    },

    /**
     * Sintetizador de sonido sutil de burbuja / pop (Cero archivos externos mp3).
     */
    reproducirSonidoAsistente() {
      if (!this.asistenteSonidoHabilitado) return;
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;

        if (!this.asistenteAudioCtx) {
          this.asistenteAudioCtx = new AudioCtx();
        }

        if (this.asistenteAudioCtx.state === 'suspended') {
          this.asistenteAudioCtx.resume();
        }

        const osc = this.asistenteAudioCtx.createOscillator();
        const gain = this.asistenteAudioCtx.createGain();

        const t = this.asistenteAudioCtx.currentTime;
        osc.type = 'sine';
        // Tono juguetón ascendente rápido tipo "pop/blip"
        osc.frequency.setValueAtTime(420, t);
        osc.frequency.exponentialRampToValueAtTime(840, t + 0.08);

        gain.gain.setValueAtTime(0.08, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.12);

        osc.connect(gain);
        gain.connect(this.asistenteAudioCtx.destination);

        osc.start(t);
        osc.stop(t + 0.13);
      } catch (e) {
        // Navegador con políticas estrictas de audio, ignorar de forma segura
      }
    }
  }
};
