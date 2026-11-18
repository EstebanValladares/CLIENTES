/**
 * KHIARA Widget Flotante Transparente.
 * - La gatita real de Rive vive directamente en la esquina (sin círculo ni emoji).
 * - Al hacer clic en la gatita, se despliega un chat compacto a su lado izquierdo.
 * - Sin desenfocar el dashboard (fondo 100% nítido).
 * - Clic fuera del chat lo cierra automáticamente.
 */

(function () {
  if (document.getElementById('khiara-widget-container')) return;

  const HOST = typeof window.KHIARA_SERVER_URL === 'string' ? window.KHIARA_SERVER_URL : 'http://localhost:8501';

  // Inyectar script de Rive si no existe
  if (!window.rive) {
    const riveScript = document.createElement('script');
    riveScript.src = 'https://unpkg.com/@rive-app/canvas@2.9.1';
    document.head.appendChild(riveScript);
  }

  // Estilos del Widget
  const style = document.createElement('style');
  style.textContent = `
    /* Contenedor transparente de la gatita flotante */
    .khiara-cat-trigger {
      position: fixed;
      bottom: 12px;
      right: 12px;
      width: 110px;
      height: 110px;
      cursor: pointer;
      z-index: 99999;
      background: transparent;
      transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
      filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.4));
    }
    .khiara-cat-trigger:hover {
      transform: scale(1.08) translateY(-4px);
    }
    .khiara-cat-canvas {
      width: 100%;
      height: 100%;
      display: block;
      background: transparent;
      pointer-events: auto;
    }
    .khiara-live-pill {
      position: absolute;
      top: 6px;
      right: 10px;
      background: #10b981;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      border: 2px solid #090d16;
      box-shadow: 0 0 10px #10b981;
      animation: khiaraPulse 2s infinite;
    }
    @keyframes khiaraPulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(0.85); }
    }

    /* Ventana de Chat Compacta Flotando al LADO IZQUIERDO de la gatita */
    .khiara-chat-panel {
      position: fixed;
      bottom: 20px;
      right: 130px; /* Al lado de la gatita */
      width: 350px;
      height: 480px;
      background: #0f172a; /* Fondo sólido oscuro sin blur en el dashboard */
      border: 1px solid rgba(56, 189, 248, 0.35);
      border-radius: 20px;
      box-shadow: 0 16px 45px rgba(0, 0, 0, 0.6), 0 0 20px rgba(56, 189, 248, 0.15);
      z-index: 99998;
      display: none;
      flex-direction: column;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      animation: khiaraSlideIn 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    @keyframes khiaraSlideIn {
      from { opacity: 0; transform: translateX(18px) scale(0.96); }
      to { opacity: 1; transform: translateX(0) scale(1); }
    }

    /* Cabecera del Chat */
    .khiara-chat-header {
      padding: 10px 14px;
      background: #1e293b;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #fff;
    }
    .khiara-header-left {
      display: flex;
      align-items: center;
      gap: 7px;
    }
    .khiara-title {
      font-size: 13px;
      font-weight: 700;
      color: #f1f5f9;
    }
    .khiara-badge {
      font-size: 9px;
      background: rgba(56, 189, 248, 0.2);
      color: #38bdf8;
      padding: 1px 6px;
      border-radius: 999px;
      font-weight: 700;
    }
    .khiara-btn-gmail {
      background: rgba(244, 114, 182, 0.15);
      border: 1px solid rgba(244, 114, 182, 0.4);
      color: #f472b6;
      border-radius: 6px;
      padding: 3px 7px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 3px;
      transition: all 0.2s ease;
    }
    .khiara-btn-gmail:hover {
      background: rgba(244, 114, 182, 0.3);
    }
    .khiara-close-btn {
      background: none;
      border: none;
      color: #94a3b8;
      font-size: 18px;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
    }
    .khiara-close-btn:hover {
      color: #fff;
    }

    /* Mensajes */
    .khiara-chat-messages {
      flex: 1;
      padding: 12px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 9px;
      font-size: 12.5px;
      background: #090d16;
    }
    .khiara-msg-user {
      align-self: flex-end;
      background: #0284c7;
      color: #fff;
      padding: 8px 12px;
      border-radius: 14px 14px 2px 14px;
      max-width: 82%;
      line-height: 1.4;
      word-break: break-word;
    }
    .khiara-msg-bot {
      align-self: flex-start;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: #f1f5f9;
      padding: 8px 12px;
      border-radius: 14px 14px 14px 2px;
      max-width: 88%;
      line-height: 1.4;
      word-break: break-word;
    }
    .khiara-msg-bot strong {
      color: #38bdf8;
    }

    /* Barra de Input */
    .khiara-input-bar {
      padding: 8px 10px;
      background: #111827;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      gap: 6px;
    }
    .khiara-input-field {
      flex: 1;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 8px 10px;
      color: #fff;
      outline: none;
      font-size: 12.5px;
    }
    .khiara-input-field:focus {
      border-color: #38bdf8;
      background: rgba(255, 255, 255, 0.08);
    }
    .khiara-send-btn {
      background: #38bdf8;
      border: none;
      border-radius: 10px;
      padding: 0 12px;
      color: #0f172a;
      font-weight: 700;
      cursor: pointer;
      font-size: 13px;
      transition: all 0.2s ease;
    }
    .khiara-send-btn:hover {
      background: #7dd3fc;
    }
  `;
  document.head.appendChild(style);

  // Crear elementos en el DOM
  const container = document.createElement('div');
  container.id = 'khiara-widget-container';
  container.innerHTML = `
    <!-- Gatita flotando en la esquina (transparente, sin círculo) -->
    <div class="khiara-cat-trigger" id="khiara-cat-btn" title="Haz clic para hablar con KHIARA">
      <canvas id="khiara-floating-cat-canvas" class="khiara-cat-canvas"></canvas>
      <div class="khiara-live-pill" title="KHIARA activa"></div>
    </div>

    <!-- Panel de Chat flotando al lado izquierdo -->
    <div class="khiara-chat-panel" id="khiara-chat-window">
      <div class="khiara-chat-header">
        <div class="khiara-header-left">
          <span>🐾</span>
          <span class="khiara-title">KHIARA</span>
          <span class="khiara-badge">IA</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
          <button class="khiara-btn-gmail" id="khiara-btn-limpiar" title="Reiniciar chat" style="border-color: rgba(148, 163, 184, 0.3); color: #94a3b8;">
            🗑️
          </button>
          <button class="khiara-btn-gmail" id="khiara-btn-gmail" title="Conectar Gmail">
            ✉️ Gmail
          </button>
          <button class="khiara-close-btn" id="khiara-close-btn">&times;</button>
        </div>
      </div>

      <div class="khiara-chat-messages" id="khiara-messages-list">
        <div class="khiara-msg-bot">
          ¡Miau! Hola Esteban, soy <strong>KHIARA</strong>. 🐾<br>
          Estoy al pendiente del sistema y de tu correo. ¿En qué te ayudo?
        </div>
      </div>

      <form class="khiara-input-bar" id="khiara-chat-form">
        <input type="text" class="khiara-input-field" id="khiara-text-input" placeholder="Escribe a KHIARA..." autocomplete="off" />
        <button type="submit" class="khiara-send-btn">➤</button>
      </form>
    </div>
  `;
  document.body.appendChild(container);

  const catBtn = document.getElementById('khiara-cat-btn');
  const chatWindow = document.getElementById('khiara-chat-window');
  const closeBtn = document.getElementById('khiara-close-btn');
  const gmailBtn = document.getElementById('khiara-btn-gmail');
  const form = document.getElementById('khiara-chat-form');
  const input = document.getElementById('khiara-text-input');
  const msgs = document.getElementById('khiara-messages-list');
  const canvas = document.getElementById('khiara-floating-cat-canvas');

  let riveInstance = null;
  let smInputs = [];

  // Inicializar la gatita Rive en la esquina directamente
  function initCatRive() {
    if (!window.rive || riveInstance) return;
    try {
      riveInstance = new window.rive.Rive({
        src: `${HOST}/static/khiara_gatita.riv`,
        canvas: canvas,
        autoplay: true,
        stateMachines: 'State Machine 1',
        onLoad: () => {
          riveInstance.resizeDrawingSurfaceToCanvas();
          smInputs = riveInstance.stateMachineInputs('State Machine 1');
        }
      });
    } catch (e) {
      console.warn('Rive esperando carga...', e);
    }
  }

  // Si Rive ya está en window, inicializar; si no, esperar
  if (window.rive) {
    initCatRive();
  } else {
    window.addEventListener('load', initCatRive);
    setTimeout(initCatRive, 500);
  }

  // Abrir / Cerrar al hacer clic en la gatita
  catBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isVisible = chatWindow.style.display === 'flex';
    chatWindow.style.display = isVisible ? 'none' : 'flex';
    if (!isVisible) {
      input.focus();
      // Disparar animación de bienvenida en la gatita
      triggerCatAction(['Click Meow hitbox', 'Forehead click']);
    }
  });

  // Botón X para cerrar
  closeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    chatWindow.style.display = 'none';
  });

  // Cerrar automáticamente al hacer clic FUERA del chat (Click Outside)
  document.addEventListener('click', (e) => {
    if (chatWindow.style.display === 'flex') {
      if (!chatWindow.contains(e.target) && !catBtn.contains(e.target)) {
        chatWindow.style.display = 'none';
      }
    }
  });

  // Evitar que clics dentro del chat lo cierren
  chatWindow.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  const limpiarBtn = document.getElementById('khiara-btn-limpiar');
  if (limpiarBtn) {
    limpiarBtn.addEventListener('click', async () => {
      try { await fetch(`${HOST}/api/chat/limpiar`, { method: 'POST' }); } catch(e){}
      msgs.innerHTML = `
        <div class="khiara-msg-bot">
          ¡Miau! Conversación reiniciada. 🐾<br>
          Estoy al pendiente del sistema y de tu correo. ¿En qué te ayudo?
        </div>
      `;
    });
  }

  // Botón Gmail: guía interactiva dentro del chat
  gmailBtn.addEventListener('click', () => {
    const guiaDiv = document.createElement('div');
    guiaDiv.className = 'khiara-msg-bot';
    guiaDiv.innerHTML = `
      <strong>📬 Conectar tu Gmail:</strong><br><br>
      Escribe tus datos en el chat con este formato:<br>
      <code>configurar gmail mi_correo@gmail.com xxxx xxxx xxxx xxxx</code><br><br>
      <em>(La clave de 16 caracteres se genera en <a href="https://myaccount.google.com/apppasswords" target="_blank" style="color:#38bdf8;">Google App Passwords</a>).</em>
    `;
    msgs.appendChild(guiaDiv);
    msgs.scrollTop = msgs.scrollHeight;
    input.value = 'configurar gmail mi_correo@gmail.com ';
    input.focus();
  });

  function triggerCatAction(names) {
    if (!smInputs) return;
    for (const inp of smInputs) {
      if (names.includes(inp.name) && typeof inp.fire === 'function') {
        inp.fire();
        break;
      }
    }
  }

  // Enviar mensaje a KHIARA
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const txt = input.value.trim();
    if (!txt) return;

    // Mensaje de usuario
    const u = document.createElement('div');
    u.className = 'khiara-msg-user';
    u.textContent = txt;
    msgs.appendChild(u);
    input.value = '';
    msgs.scrollTop = msgs.scrollHeight;

    // Estado pensando de la gatita
    const b = document.createElement('div');
    b.className = 'khiara-msg-bot';
    b.innerHTML = '<em>KHIARA pensando... 🐾</em>';
    msgs.appendChild(b);
    msgs.scrollTop = msgs.scrollHeight;

    triggerCatAction(['Forehead click', 'Click Meow hitbox']);

    try {
      const res = await fetch(`${HOST}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensaje: txt })
      });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let acumulado = '';
      b.textContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value);
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const d = JSON.parse(line.substring(6));
              if (d.tipo === 'texto') {
                acumulado += d.valor;
                b.innerHTML = acumulado
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\n/g, '<br>');
                msgs.scrollTop = msgs.scrollHeight;
              }
            } catch (err) {}
          }
        }
      }
    } catch (err) {
      b.innerHTML = `<span style="color:#ef4444;">Error: ${err.message}</span>`;
    }
  });
})();
