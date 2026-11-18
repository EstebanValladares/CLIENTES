/**
 * Módulo Frontend de KHIARA para Vue 3.
 * Gestiona el avatar flotante, estado en vivo, chat y recepción de notificaciones.
 */

window.createKhiaraModule = function(Vue, context) {
  const { ref, computed, onMounted } = Vue;

  const khiaraOnline = ref(false);
  const khiaraChatAbierto = ref(false);
  const khiaraCargando = ref(false);
  const khiaraInput = ref('');
  const khiaraNotificaciones = ref([]);
  const khiaraNotifNoLeidas = ref(0);
  const khiaraGloboAlerta = ref(null); // Alerta emergente sobre el avatar
  const khiaraUltimoIdNotif = ref('');

  const obtenerHoraActual = () => {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const khiaraMensajes = ref([
    {
      id: 1,
      remitente: 'khiara',
      texto: '¡Hola! Soy **KHIARA**. Estoy conectada como tu asistente de ingeniería y análisis. ¿En qué te puedo apoyar hoy?',
      hora: obtenerHoraActual()
    }
  ]);

  // Verificar estado del microservicio KHIARA
  const verificarEstadoKhiara = async () => {
    try {
      const res = await fetch('/api/khiara/status');
      if (res.ok) {
        const data = await res.json();
        khiaraOnline.value = !!data.online;
      } else {
        khiaraOnline.value = false;
      }
    } catch (e) {
      khiaraOnline.value = false;
    }
  };

  // Consultar notificaciones en segundo plano
  const consultarNotificacionesKhiara = async () => {
    try {
      const res = await fetch('/api/khiara/notificaciones');
      if (res.ok) {
        const data = await res.json();
        const lista = data.notificaciones || [];
        khiaraNotificaciones.value = lista;

        if (lista.length > 0) {
          const masReciente = lista[0];
          if (masReciente.id !== khiaraUltimoIdNotif.value) {
            khiaraUltimoIdNotif.value = masReciente.id;
            khiaraNotifNoLeidas.value = lista.length;
            // Mostrar globo emergente si el chat está cerrado
            if (!khiaraChatAbierto.value) {
              khiaraGloboAlerta.value = masReciente;
              // Auto-ocultar globo después de 8 segundos
              setTimeout(() => {
                khiaraGloboAlerta.value = null;
              }, 8000);
            }
          }
        }
      }
    } catch (e) {
      // Silencioso
    }
  };

  const toggleChatKhiara = () => {
    khiaraChatAbierto.value = !khiaraChatAbierto.value;
    if (khiaraChatAbierto.value) {
      khiaraGloboAlerta.value = null;
      khiaraNotifNoLeidas.value = 0;
      verificarEstadoKhiara();
    }
  };

  const enviarMensajeKhiara = async () => {
    const txt = (khiaraInput.value || '').trim();
    if (!txt || khiaraCargando.value) return;

    // Agregar mensaje del usuario al chat
    khiaraMensajes.value.push({
      id: Date.now(),
      remitente: 'usuario',
      texto: txt,
      hora: obtenerHoraActual()
    });
    khiaraInput.value = '';
    khiaraCargando.value = true;

    // Scroll automático
    setTimeout(() => {
      const el = document.getElementById('khiara-mensajes-container');
      if (el) el.scrollTop = el.scrollHeight;
    }, 50);

    try {
      const res = await fetch('/api/khiara/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje: txt, usuario: 'Esteban' })
      });

      if (res.ok) {
        const data = await res.json();
        khiaraMensajes.value.push({
          id: Date.now() + 1,
          remitente: 'khiara',
          texto: data.respuesta || 'Sin respuesta.',
          hora: obtenerHoraActual()
        });
      } else {
        khiaraMensajes.value.push({
          id: Date.now() + 1,
          remitente: 'khiara',
          texto: '⚠ No pude obtener respuesta de KHIARA. Revisa que el microservicio esté encendido (`python run.py --server`).',
          hora: obtenerHoraActual()
        });
      }
    } catch (err) {
      khiaraMensajes.value.push({
        id: Date.now() + 1,
        remitente: 'khiara',
        texto: '⚠ Error de conexión con KHIARA: ' + err.message,
        hora: obtenerHoraActual()
      });
    } finally {
      khiaraCargando.value = false;
      setTimeout(() => {
        const el = document.getElementById('khiara-mensajes-container');
        if (el) el.scrollTop = el.scrollHeight;
      }, 50);
    }
  };

  const limpiarHistorialKhiara = () => {
    khiaraMensajes.value = [
      {
        id: 1,
        remitente: 'khiara',
        texto: 'Historial reiniciado. ¿Qué deseas consultar ahora?',
        hora: obtenerHoraActual()
      }
    ];
  };

  // Formateador simple de Markdown a HTML seguro
  const formatearMarkdownKhiara = (texto) => {
    if (!texto) return '';
    let html = texto
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Negritas **texto**
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Cursivas *texto*
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Código en línea `codigo`
    html = html.replace(/`([^`]+)`/g, '<code class="bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 px-1 py-0.5 rounded text-xs font-mono">$1</code>');
    // Listas con viñetas • o *
    html = html.replace(/^[•*]\s+(.*)$/gm, '<li class="ml-4 list-disc">$1</li>');
    // Saltos de línea
    html = html.replace(/\n/g, '<br/>');

    return html;
  };

  // Sondeo periódico cada 5 segundos
  setInterval(() => {
    verificarEstadoKhiara();
    consultarNotificacionesKhiara();
  }, 5000);

  // Verificación inicial
  verificarEstadoKhiara();
  consultarNotificacionesKhiara();

  return {
    khiaraOnline,
    khiaraChatAbierto,
    khiaraCargando,
    khiaraInput,
    khiaraMensajes,
    khiaraNotificaciones,
    khiaraNotifNoLeidas,
    khiaraGloboAlerta,
    toggleChatKhiara,
    enviarMensajeKhiara,
    limpiarHistorialKhiara,
    formatearMarkdownKhiara
  };
};
