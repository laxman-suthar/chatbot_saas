(function () {
  'use strict';

  const scriptTag = document.currentScript ||
    (function () {
      const scripts = document.getElementsByTagName('script');
      return scripts[scripts.length - 1];
    })();

  const API_KEY = scriptTag.getAttribute('data-api-key');
  const WS_HOST = scriptTag.getAttribute('data-ws-host') || window.location.host;
  const WEBSITE_ID = scriptTag.getAttribute('data-website-id');

  if (!API_KEY) {
    console.warn('[ChatWidget] Missing data-api-key attribute.');
    return;
  }

  // ── Inject styles into <head> (more reliable than innerHTML) ──────────────
  const CSS = `
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');

    #cw-root * { box-sizing: border-box; margin: 0; padding: 0; font-family: "DM Sans", sans-serif; }

    #cw-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: #1a1a2e;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2147483646;
      border: none;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    #cw-launcher:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(0,0,0,0.38); }
    #cw-launcher svg { transition: transform 0.3s ease, opacity 0.3s ease; }
    #cw-launcher.open .cw-icon-chat   { transform: scale(0); opacity: 0; position: absolute; }
    #cw-launcher.open .cw-icon-close  { transform: scale(1); opacity: 1; }
    #cw-launcher:not(.open) .cw-icon-close { transform: scale(0); opacity: 0; position: absolute; }
    #cw-launcher:not(.open) .cw-icon-chat  { transform: scale(1); opacity: 1; }

    #cw-badge {
      position: absolute;
      top: 2px; right: 2px;
      width: 18px; height: 18px;
      background: #e74c3c;
      color: #fff;
      font-size: 10px;
      font-weight: 600;
      border-radius: 50%;
      display: none;
      align-items: center;
      justify-content: center;
      border: 2px solid #fff;
    }
    #cw-badge.visible { display: flex; }

    #cw-panel {
      position: fixed;
      bottom: 92px;
      right: 24px;
      width: 360px;
      height: 520px;
      background: #fff;
      border-radius: 18px;
      box-shadow: 0 8px 48px rgba(0,0,0,0.18);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 2147483645;
      transform: scale(0.92) translateY(16px);
      transform-origin: bottom right;
      opacity: 0;
      pointer-events: none;
      transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), opacity 0.2s ease;
    }
    #cw-panel.open {
      transform: scale(1) translateY(0);
      opacity: 1;
      pointer-events: all;
    }

    #cw-header {
      background: #1a1a2e;
      color: #fff;
      padding: 14px 18px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }
    #cw-avatar {
      width: 36px; height: 36px;
      border-radius: 50%;
      background: linear-gradient(135deg, #6c63ff, #e040fb);
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    #cw-header-info { flex: 1; min-width: 0; }
    #cw-title { font-size: 14px; font-weight: 600; line-height: 1.2; }
    #cw-status-text { font-size: 11px; color: #a0a8c0; margin-top: 2px; }
    #cw-header-close {
      background: none; border: none; cursor: pointer;
      color: #a0a8c0; display: flex; align-items: center;
      padding: 4px; border-radius: 6px;
      transition: color 0.15s, background 0.15s;
    }
    #cw-header-close:hover { color: #fff; background: rgba(255,255,255,0.1); }

    #cw-messages {
      flex: 1;
      overflow-y: auto;
      padding: 20px 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #f7f8fc;
    }
    #cw-messages::-webkit-scrollbar { width: 4px; }
    #cw-messages::-webkit-scrollbar-thumb { background: #d0d4e4; border-radius: 4px; }

    @keyframes cw-pop {
      from { transform: scale(0.94); opacity: 0; }
      to   { transform: scale(1);    opacity: 1; }
    }

    .cw-msg {
      max-width: 82%;
      padding: 12px 16px;
      border-radius: 18px;
      font-size: 14px;
      line-height: 1.6;
      word-break: break-word;
      animation: cw-pop 0.18s ease;
    }
    .cw-msg.user {
      background: #1a1a2e !important;
      color: #ffffff !important;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .cw-msg.assistant {
      background: #ffffff !important;
      color: #1a1a2e !important;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.09);
    }
    .cw-msg.system {
      background: #eef0ff !important;
      color: #5c6bc0 !important;
      align-self: center;
      font-size: 11px;
      border-radius: 8px;
      padding: 6px 12px;
    }

    #cw-typing {
      display: none;
      align-self: flex-start;
      background: #fff;
      padding: 10px 16px;
      border-radius: 16px;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    #cw-typing.visible { display: flex; gap: 4px; align-items: center; }
    .cw-dot {
      width: 7px; height: 7px;
      border-radius: 50%;
      background: #c0c4d4;
      animation: cw-bounce 1.2s infinite;
    }
    .cw-dot:nth-child(2) { animation-delay: 0.2s; }
    .cw-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes cw-bounce {
      0%,60%,100% { transform: translateY(0); }
      30%          { transform: translateY(-5px); }
    }

    #cw-input-area {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 12px;
      border-top: 1px solid #edeef5;
      background: #fff;
      flex-shrink: 0;
    }
    #cw-input {
      flex: 1;
      padding: 9px 14px;
      border: 1.5px solid #e0e2ef;
      border-radius: 22px;
      font-size: 13.5px;
      color: #1a1a2e;
      outline: none;
      background: #f7f8fc;
      transition: border-color 0.15s;
    }
    #cw-input:focus { border-color: #6c63ff; background: #fff; }
    #cw-input::placeholder { color: #b0b4c8; }
    #cw-send {
      width: 38px; height: 38px;
      border-radius: 50%;
      background: #1a1a2e;
      border: none;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
      transition: background 0.15s, transform 0.15s;
    }
    #cw-send:hover { background: #6c63ff; transform: scale(1.06); }
    #cw-send:disabled { background: #c0c4d4; cursor: not-allowed; transform: none; }

    #cw-footer {
      text-align: center;
      font-size: 10px;
      color: #b0b4c8;
      padding: 5px 0 8px;
      background: #fff;
      letter-spacing: 0.02em;
    }

    @media (max-width: 400px) {
      #cw-panel { width: calc(100vw - 16px); right: 8px; bottom: 80px; }
      #cw-launcher { right: 12px; bottom: 12px; }
    }

    .cw-msg.assistant ul { padding-left: 18px; margin: 4px 0; }
    .cw-msg.assistant li { margin: 3px 0; }
    .cw-msg.assistant strong { font-weight: 600; }
    .cw-msg.assistant em { font-style: italic; }
    .cw-msg.assistant code {
      background: #f0f1f7;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 12px;
      font-family: monospace;
    }
  `;

  function injectStyles() {
    const style = document.createElement('style');
    style.id = 'cw-styles';
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  // ── HTML ──────────────────────────────────────────────────────────────────
  function buildHTML() {
    return `
      <!-- Launcher -->
      <button id="cw-launcher" aria-label="Open chat">
        <span id="cw-badge"></span>
        <svg class="cw-icon-chat" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <svg class="cw-icon-close" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>

      <!-- Panel -->
      <div id="cw-panel" role="dialog" aria-label="Chat support">
        <div id="cw-header">
          <div id="cw-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"/><path d="M12 12 2.1 9.1"/>
            </svg>
          </div>
          <div id="cw-header-info">
            <div id="cw-title">Support Chat</div>
            <div id="cw-status-text">Connecting…</div>
          </div>
          <button id="cw-header-close" aria-label="Close chat">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div id="cw-messages">
          <div id="cw-typing">
            <span class="cw-dot"></span>
            <span class="cw-dot"></span>
            <span class="cw-dot"></span>
          </div>
        </div>

        <div id="cw-input-area">
          <input id="cw-input" type="text" placeholder="Type a message…" autocomplete="off" />
          <button id="cw-send" aria-label="Send">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div id="cw-footer">Powered by AI Chat</div>
      </div>
    `;
  }

  // ── Widget logic ──────────────────────────────────────────────────────────
  function init(websiteId) {
    injectStyles();

    const root = document.createElement('div');
    root.id = 'cw-root';
    root.innerHTML = buildHTML();
    document.body.appendChild(root);

    const launcher = document.getElementById('cw-launcher');
    const panel = document.getElementById('cw-panel');
    const badge = document.getElementById('cw-badge');
    const messages = document.getElementById('cw-messages');
    const input = document.getElementById('cw-input');
    const sendBtn = document.getElementById('cw-send');
    const headerClose = document.getElementById('cw-header-close');
    const statusText = document.getElementById('cw-status-text');
    const typing = document.getElementById('cw-typing');

    // Force flex layout on messages container — bypasses any page CSS resets
    messages.style.cssText = 'flex:1;overflow-y:auto;padding:20px 16px;display:flex;flex-direction:column;gap:12px;background:#f7f8fc;';

    let ws = null;
    let isOpen = false;
    let unread = 0;
    let reconnectTimer = null;

    function togglePanel() {
      isOpen = !isOpen;
      panel.classList.toggle('open', isOpen);
      launcher.classList.toggle('open', isOpen);
      if (isOpen) {
        clearUnread();
        input.focus();
        scrollBottom();
      }
    }

    launcher.addEventListener('click', togglePanel);
    headerClose.addEventListener('click', togglePanel);

    document.addEventListener('click', function (e) {
      if (isOpen && !panel.contains(e.target) && !launcher.contains(e.target)) {
        togglePanel();
      }
    });

    function addUnread() {
      if (isOpen) return;
      unread++;
      badge.textContent = unread > 9 ? '9+' : unread;
      badge.classList.add('visible');
    }
    function clearUnread() {
      unread = 0;
      badge.classList.remove('visible');
    }

    function parseMarkdown(text) {
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/_(.*?)_/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/^\s*[\*\-]\s+(.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n/g, '<br>');
    }

    function addMessage(role, text) {
      const div = document.createElement('div');
      div.className = 'cw-msg ' + role;

      // Base styles applied inline so page CSS cannot override them
      const base = [
        'max-width:82%',
        'padding:12px 16px',
        'border-radius:18px',
        'font-size:14px',
        'line-height:1.6',
        'word-break:break-word',
        'font-family:"DM Sans",sans-serif',
        'display:inline-block',
      ];

      if (role === 'user') {
        base.push(
          'background:#1a1a2e',
          'color:#ffffff',
          'align-self:flex-end',
          'border-bottom-right-radius:4px',
          'margin-left:auto'
        );
        div.textContent = text;
      } else if (role === 'assistant') {
        base.push(
          'background:#ffffff',
          'color:#1a1a2e',
          'align-self:flex-start',
          'border-bottom-left-radius:4px',
          'box-shadow:0 2px 8px rgba(0,0,0,0.09)',
          'margin-right:auto'
        );
        div.innerHTML = parseMarkdown(text);
      } else {
        base.push(
          'background:#eef0ff',
          'color:#5c6bc0',
          'align-self:center',
          'font-size:11px',
          'border-radius:8px',
          'padding:6px 12px',
          'margin:0 auto'
        );
        div.textContent = text;
      }

      div.style.cssText = base.join(';');
      messages.insertBefore(div, typing);
      scrollBottom();
      if (role === 'assistant') addUnread();
    }

    function scrollBottom() {
      messages.scrollTop = messages.scrollHeight;
    }

    function setStatus(text) {
      statusText.textContent = text;
    }

    function showTyping(show) {
      typing.classList.toggle('visible', show);
      if (show) scrollBottom();
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const WS_URL = `${wsProtocol}://${WS_HOST}/ws/chat/${websiteId}/?api_key=${API_KEY}`;

    function connect() {
      setStatus('Connecting…');
      ws = new WebSocket(WS_URL);

      ws.onopen = function () {
        setStatus('Online · Ready to help');
        sendBtn.disabled = false;
      };

      ws.onmessage = function (event) {
        try {
          const data = JSON.parse(event.data);
          showTyping(false);
          if (data.type === 'connection_established' || data.type === 'message') {
            addMessage('assistant', data.message);
          } else if (data.type === 'typing') {
            showTyping(true);
          } else if (data.type === 'error') {
            addMessage('system', '⚠ ' + data.message);
          }
        } catch (e) {
          console.warn('[ChatWidget] Bad message:', e);
        }
      };

      ws.onclose = function () {
        setStatus('Disconnected — retrying…');
        sendBtn.disabled = true;
        showTyping(false);
        reconnectTimer = setTimeout(connect, 3500);
      };

      ws.onerror = function () {
        setStatus('Connection error');
        sendBtn.disabled = true;
      };
    }

    function send() {
      const text = input.value.trim();
      if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
      addMessage('user', text);
      ws.send(JSON.stringify({ message: text }));
      input.value = '';
      showTyping(true);
    }

    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });

    sendBtn.disabled = true;
    connect();
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  if (WEBSITE_ID) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { init(WEBSITE_ID); });
    } else {
      init(WEBSITE_ID);
    }
  } else {
    const scriptSrc = scriptTag.src;
    const baseUrl = scriptSrc.substring(0, scriptSrc.lastIndexOf('/static/'));

    fetch(baseUrl + '/api/websites/resolve/?api_key=' + API_KEY)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.website_id) {
          if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function () { init(data.website_id); });
          } else {
            init(data.website_id);
          }
        } else {
          console.warn('[ChatWidget] Could not resolve website ID. Add data-website-id to your script tag.');
        }
      })
      .catch(function () {
        console.warn('[ChatWidget] API unreachable. Add data-website-id to your script tag as a fallback.');
      });
  }

})();