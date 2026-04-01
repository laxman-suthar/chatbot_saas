(function () {
  'use strict';

  const scriptTag = document.currentScript ||
    (function () {
      const scripts = document.getElementsByTagName('script');
      return scripts[scripts.length - 1];
    })();

  const API_KEY    = scriptTag.getAttribute('data-api-key');
  const WS_HOST    = scriptTag.getAttribute('data-ws-host') || window.location.host;
  const WEBSITE_ID = scriptTag.getAttribute('data-website-id');

  if (!API_KEY) { console.warn('[ChatWidget] Missing data-api-key attribute.'); return; }

  const CSS = `
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');
    #cw-root * { box-sizing: border-box; margin: 0; padding: 0; font-family: "DM Sans", sans-serif; }
    #cw-launcher {
      position: fixed; bottom: 24px; right: 24px; width: 56px; height: 56px; border-radius: 50%;
      background: #1a1a2e; box-shadow: 0 4px 20px rgba(0,0,0,0.3); cursor: pointer;
      display: flex; align-items: center; justify-content: center; z-index: 2147483646; border: none;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    #cw-launcher:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(0,0,0,0.38); }
    #cw-launcher svg { transition: transform 0.3s ease, opacity 0.3s ease; }
    #cw-launcher.open .cw-icon-chat   { transform: scale(0); opacity: 0; position: absolute; }
    #cw-launcher.open .cw-icon-close  { transform: scale(1); opacity: 1; }
    #cw-launcher:not(.open) .cw-icon-close { transform: scale(0); opacity: 0; position: absolute; }
    #cw-launcher:not(.open) .cw-icon-chat  { transform: scale(1); opacity: 1; }
    #cw-badge {
      position: absolute; top: 2px; right: 2px; width: 18px; height: 18px;
      background: #e74c3c; color: #fff; font-size: 10px; font-weight: 600;
      border-radius: 50%; display: none; align-items: center; justify-content: center; border: 2px solid #fff;
    }
    #cw-badge.visible { display: flex; }
    #cw-panel {
      position: fixed; bottom: 92px; right: 24px; width: 360px; height: 520px;
      background: #fff; border-radius: 18px; box-shadow: 0 8px 48px rgba(0,0,0,0.18);
      display: flex; flex-direction: column; overflow: hidden; z-index: 2147483645;
      transform: scale(0.92) translateY(16px); transform-origin: bottom right;
      opacity: 0; pointer-events: none;
      transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), opacity 0.2s ease;
    }
    #cw-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }
    #cw-header {
      background: #1a1a2e; color: #fff; padding: 14px 18px;
      display: flex; align-items: center; gap: 12px; flex-shrink: 0;
    }
    #cw-avatar {
      width: 36px; height: 36px; border-radius: 50%;
      background: linear-gradient(135deg, #6c63ff, #e040fb);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    #cw-header-info { flex: 1; min-width: 0; }
    #cw-title { font-size: 14px; font-weight: 600; line-height: 1.2; }
    #cw-status-text { font-size: 11px; color: #a0a8c0; margin-top: 2px; }
    #cw-header-close {
      background: none; border: none; cursor: pointer; color: #a0a8c0;
      display: flex; align-items: center; padding: 4px; border-radius: 6px;
      transition: color 0.15s, background 0.15s;
    }
    #cw-header-close:hover { color: #fff; background: rgba(255,255,255,0.1); }
    #cw-messages {
      flex: 1; overflow-y: auto; padding: 16px 14px;
      display: flex; flex-direction: column; gap: 10px; background: #f7f8fc;
    }
    #cw-messages::-webkit-scrollbar { width: 4px; }
    #cw-messages::-webkit-scrollbar-thumb { background: #d0d4e4; border-radius: 4px; }
    .cw-msg {
      max-width: 82%; padding: 10px 14px; border-radius: 16px;
      font-size: 13.5px; line-height: 1.5; word-break: break-word; animation: cw-pop 0.18s ease;
    }
    @keyframes cw-pop { from { transform: scale(0.94); opacity: 0; } to { transform: scale(1); opacity: 1; } }
    .cw-msg.user { background: #1a1a2e; color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
    .cw-msg.assistant { background: #fff; color: #1a1a2e; align-self: flex-start; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }
    .cw-msg.system { background: #eef0ff; color: #5c6bc0; align-self: center; font-size: 11px; border-radius: 8px; padding: 6px 12px; }

    .cw-callback-card {
      align-self: flex-start; background: #fff; border-radius: 16px; border-bottom-left-radius: 4px;
      box-shadow: 0 2px 14px rgba(0,0,0,0.10); padding: 16px 16px 14px; width: 95%;
      animation: cw-pop 0.18s ease;
    }
    .cw-cb-header { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
    .cw-cb-header-icon {
      width: 28px; height: 28px; border-radius: 8px; flex-shrink: 0;
      background: linear-gradient(135deg, #6c63ff, #e040fb);
      display: flex; align-items: center; justify-content: center;
    }
    .cw-cb-title { font-size: 13.5px; font-weight: 600; color: #1a1a2e; }
    .cw-cb-subtitle { font-size: 11.5px; color: #999; margin-bottom: 13px; line-height: 1.4; }
    .cw-cb-field { margin-bottom: 8px; }
    .cw-cb-field label {
      display: flex; align-items: center; gap: 3px;
      font-size: 10.5px; font-weight: 600; color: #6c63ff;
      margin-bottom: 4px; letter-spacing: 0.04em; text-transform: uppercase;
    }
    .cw-required { color: #e74c3c; font-size: 12px; line-height: 1; }
    .cw-cb-field input, .cw-cb-field select {
      width: 100%; padding: 8px 11px;
      border: 1.5px solid #e0e2ef; border-radius: 9px;
      font-size: 13px; color: #1a1a2e; background: #f7f8fc; outline: none;
      transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
      -webkit-appearance: none; appearance: none;
    }
    .cw-cb-field input:focus, .cw-cb-field select:focus {
      border-color: #6c63ff; background: #fff;
      box-shadow: 0 0 0 3px rgba(108,99,255,0.12);
    }
    .cw-cb-field input.cw-error { border-color: #e74c3c; background: #fff8f8; box-shadow: 0 0 0 3px rgba(231,76,60,0.09); }
    .cw-cb-field select.cw-error { border-color: #e74c3c; background: #fff8f8; }
    .cw-cb-field input::placeholder { color: #c0c4d8; }
    .cw-select-wrap { position: relative; }
    .cw-select-wrap::after {
      content: ''; position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
      width: 0; height: 0;
      border-left: 4px solid transparent; border-right: 4px solid transparent;
      border-top: 5px solid #888; pointer-events: none;
    }
    .cw-cb-err {
      display: none; font-size: 11px; color: #e74c3c;
      margin-top: 4px; font-weight: 500; padding-left: 2px;
    }
    .cw-cb-err.show { display: block; animation: cw-pop 0.15s ease; }
    .cw-cb-row { display: flex; gap: 8px; }
    .cw-cb-row .cw-cb-field { flex: 1; min-width: 0; }
    .cw-callback-submit {
      width: 100%; margin-top: 6px; padding: 10px 14px;
      background: linear-gradient(135deg, #1a1a2e 0%, #6c63ff 100%);
      color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 600;
      cursor: pointer; transition: opacity 0.15s, transform 0.12s, box-shadow 0.15s;
      letter-spacing: 0.02em; display: flex; align-items: center; justify-content: center; gap: 7px;
    }
    .cw-callback-submit:hover:not(:disabled) {
      opacity: 0.91; transform: translateY(-1px); box-shadow: 0 4px 14px rgba(108,99,255,0.32);
    }
    .cw-callback-submit:disabled { background: #c8cad8; cursor: not-allowed; transform: none; box-shadow: none; }

    .cw-cb-success {
      display: flex; flex-direction: column; align-items: center;
      gap: 7px; padding: 6px 4px 4px; text-align: center; animation: cw-pop 0.22s ease;
    }
    .cw-cb-success-icon {
      width: 44px; height: 44px; border-radius: 50%;
      background: linear-gradient(135deg, #43e97b, #38f9d7);
      display: flex; align-items: center; justify-content: center;
    }
    .cw-cb-success strong { font-size: 13.5px; color: #1a1a2e; font-weight: 600; }
    .cw-cb-success span { font-size: 12px; color: #888; line-height: 1.5; }

    #cw-typing {
      display: none; align-self: flex-start; background: #fff; padding: 10px 16px;
      border-radius: 16px; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    }
    #cw-typing.visible { display: flex; gap: 4px; align-items: center; }
    .cw-dot { width: 7px; height: 7px; border-radius: 50%; background: #c0c4d4; animation: cw-bounce 1.2s infinite; }
    .cw-dot:nth-child(2) { animation-delay: 0.2s; }
    .cw-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes cw-bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }

    #cw-input-area {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 12px; border-top: 1px solid #edeef5; background: #fff; flex-shrink: 0;
    }
    #cw-input {
      flex: 1; padding: 9px 14px; border: 1.5px solid #e0e2ef; border-radius: 22px;
      font-size: 13.5px; color: #1a1a2e; outline: none; background: #f7f8fc; transition: border-color 0.15s;
    }
    #cw-input:focus { border-color: #6c63ff; background: #fff; }
    #cw-input::placeholder { color: #b0b4c8; }
    #cw-send {
      width: 38px; height: 38px; border-radius: 50%; background: #1a1a2e; border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      transition: background 0.15s, transform 0.15s;
    }
    #cw-send:hover { background: #6c63ff; transform: scale(1.06); }
    #cw-send:disabled { background: #c0c4d4; cursor: not-allowed; transform: none; }
    #cw-footer { text-align: center; font-size: 10px; color: #b0b4c8; padding: 5px 0 8px; background: #fff; }
    @media (max-width: 400px) {
      #cw-panel { width: calc(100vw - 16px); right: 8px; bottom: 80px; }
      #cw-launcher { right: 12px; bottom: 12px; }
    }
  `;

  const PHONE_SVG = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.65 3.35 2 2 0 0 1 3.62 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.59a16 16 0 0 0 6 6l.96-.96a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21.72 16l.2.92z"/></svg>`;

  function buildHTML() {
    return `
      <style>${CSS}</style>
      <button id="cw-launcher" aria-label="Open chat">
        <span id="cw-badge"></span>
        <svg class="cw-icon-chat" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <svg class="cw-icon-close" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <div id="cw-panel" role="dialog" aria-label="Chat support">
        <div id="cw-header">
          <div id="cw-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
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
            <span class="cw-dot"></span><span class="cw-dot"></span><span class="cw-dot"></span>
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

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function init(websiteId) {
    var root = document.createElement('div');
    root.id = 'cw-root';
    root.innerHTML = buildHTML();
    document.body.appendChild(root);

    var launcher    = document.getElementById('cw-launcher');
    var panel       = document.getElementById('cw-panel');
    var badge       = document.getElementById('cw-badge');
    var messages    = document.getElementById('cw-messages');
    var input       = document.getElementById('cw-input');
    var sendBtn     = document.getElementById('cw-send');
    var headerClose = document.getElementById('cw-header-close');
    var statusText  = document.getElementById('cw-status-text');
    var typing      = document.getElementById('cw-typing');

    var ws = null, isOpen = false, unread = 0, reconnectCount = 0;

    function togglePanel() {
      isOpen = !isOpen;
      panel.classList.toggle('open', isOpen);
      launcher.classList.toggle('open', isOpen);
      if (isOpen) { clearUnread(); input.focus(); scrollBottom(); }
    }
    launcher.addEventListener('click', togglePanel);
    headerClose.addEventListener('click', togglePanel);
    document.addEventListener('click', function (e) {
      if (isOpen && !panel.contains(e.target) && !launcher.contains(e.target)) togglePanel();
    });

    function addUnread() { if (isOpen) return; unread++; badge.textContent = unread > 9 ? '9+' : unread; badge.classList.add('visible'); }
    function clearUnread() { unread = 0; badge.classList.remove('visible'); }

    function addMessage(role, text) {
      var div = document.createElement('div');
      div.className = 'cw-msg ' + role;
      div.innerHTML = escHtml(text)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
      messages.insertBefore(div, typing);
      scrollBottom();
      if (role === 'assistant') addUnread();
    }

    function showCallbackForm(introText) {
      addMessage('assistant', introText);

      var card = document.createElement('div');
      card.className = 'cw-callback-card';
      card.innerHTML = `
        <div class="cw-cb-header">
          <div class="cw-cb-header-icon">${PHONE_SVG}</div>
          <div class="cw-cb-title">Request a Callback</div>
        </div>
        <div class="cw-cb-subtitle">Fill in your details and our team will reach out shortly.</div>

        <div class="cw-cb-field">
          <label>Full Name <span class="cw-required">*</span></label>
          <input type="text" id="cw-cb-name" placeholder="e.g. Rahul Sharma" maxlength="100" autocomplete="name" />
          <div class="cw-cb-err" id="cw-err-name"></div>
        </div>

        <div class="cw-cb-field">
          <label>Subject / Topic <span class="cw-required">*</span></label>
          <div class="cw-select-wrap">
            <select id="cw-cb-subject">
              <option value="">— Select a topic —</option>
              <option value="general">General Inquiry</option>
              <option value="support">Technical Support</option>
              <option value="billing">Billing &amp; Payments</option>
              <option value="sales">Sales &amp; Pricing</option>
              <option value="complaint">Complaint</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div class="cw-cb-err" id="cw-err-subject"></div>
        </div>

        <div class="cw-cb-row">
          <div class="cw-cb-field">
            <label>Email <span class="cw-required">*</span></label>
            <input type="email" id="cw-cb-email" placeholder="you@example.com" maxlength="150" autocomplete="email" />
            <div class="cw-cb-err" id="cw-err-email"></div>
          </div>
          <div class="cw-cb-field">
            <label>Mobile <span class="cw-required">*</span></label>
            <input type="tel" id="cw-cb-phone" placeholder="+91 98765…" maxlength="20" autocomplete="tel" />
            <div class="cw-cb-err" id="cw-err-phone"></div>
          </div>
        </div>

        <button class="cw-callback-submit" id="cw-cb-submit">
          ${PHONE_SVG} Request Callback
        </button>
      `;

      messages.insertBefore(card, typing);
      scrollBottom();

      var nameInput  = card.querySelector('#cw-cb-name');
      var subjectSel = card.querySelector('#cw-cb-subject');
      var emailInput = card.querySelector('#cw-cb-email');
      var phoneInput = card.querySelector('#cw-cb-phone');
      var errName    = card.querySelector('#cw-err-name');
      var errSubject = card.querySelector('#cw-err-subject');
      var errEmail   = card.querySelector('#cw-err-email');
      var errPhone   = card.querySelector('#cw-err-phone');
      var submitBtn  = card.querySelector('#cw-cb-submit');

      function setErr(el, errEl, msg) {
        el.classList.add('cw-error');
        errEl.textContent = msg;
        errEl.classList.add('show');
      }
      function clrErr(el, errEl) {
        el.classList.remove('cw-error');
        errEl.classList.remove('show');
      }

      nameInput.addEventListener('input',   function() { clrErr(nameInput, errName); });
      subjectSel.addEventListener('change', function() { clrErr(subjectSel, errSubject); });
      emailInput.addEventListener('input',  function() { clrErr(emailInput, errEmail); });
      phoneInput.addEventListener('input',  function() { clrErr(phoneInput, errPhone); });

      submitBtn.addEventListener('click', function () {
        var name    = nameInput.value.trim();
        var subject = subjectSel.value;
        var email   = emailInput.value.trim();
        var phone   = phoneInput.value.trim();
        var emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        var phoneRe = /^[+\d][\d\s\-().]{5,19}$/;
        var valid   = true;

        if (!name)                        { setErr(nameInput,  errName,    'Please enter your full name.');       valid = false; }
        if (!subject)                     { setErr(subjectSel, errSubject, 'Please select a topic.');             valid = false; }
        if (!email || !emailRe.test(email)) { setErr(emailInput, errEmail, 'Enter a valid email address.');       valid = false; }
        if (!phone || !phoneRe.test(phone)) { setErr(phoneInput, errPhone, 'Enter a valid phone number.');        valid = false; }

        if (!valid) { scrollBottom(); return; }

        submitBtn.disabled = true;
        submitBtn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
          Submitting…
        `;

        ws.send(JSON.stringify({ type: 'callback_form', name: name, email: email, phone: phone, subject: subject }));
      });
    }

    function replaceCardWithSuccess(phone) {
      var card = messages.querySelector('.cw-callback-card');
      if (!card) return;
      card.innerHTML = `
        <div class="cw-cb-success">
          <div class="cw-cb-success-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <strong>Request Submitted! 🎉</strong>
          <span>Our team will reach you on<br><strong>${escHtml(phone)}</strong> shortly.</span>
        </div>
      `;
      scrollBottom();
    }

    function scrollBottom() { messages.scrollTop = messages.scrollHeight; }
    function setStatus(t)   { statusText.textContent = t; }
    function showTyping(on) { typing.classList.toggle('visible', on); if (on) scrollBottom(); }

    var wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    var WS_URL = wsProtocol + '://' + WS_HOST + '/ws/chat/' + websiteId + '/?api_key=' + API_KEY;

    function connect() {
      setStatus('Connecting…');
      ws = new WebSocket(WS_URL);

      ws.onopen = function () { setStatus('Online · Ready to help'); sendBtn.disabled = false; reconnectCount = 0; };

      ws.onmessage = function (event) {
        try {
          var data = JSON.parse(event.data);
          showTyping(false);

          if (data.type === 'connection_established') {
            if (messages.querySelectorAll('.cw-msg').length === 0) addMessage('assistant', data.message);

          } else if (data.type === 'message') {
            addMessage('assistant', data.message);

          } else if (data.type === 'callback_form_request') {
            showCallbackForm(data.message);

          } else if (data.type === 'callback_form_success') {
            // Extract phone from server message e.g. "**+91 xxx**"
            var m = data.message.match(/\*\*([^*]+)\*\*/);
            replaceCardWithSuccess(m ? m[1] : '');
            addMessage('assistant', data.message);

          } else if (data.type === 'callback_form_error') {
            addMessage('system', '⚠ ' + data.message);

          } else if (data.type === 'typing') {
            showTyping(true);

          } else if (data.type === 'error') {
            addMessage('system', '⚠ ' + data.message);
          }
        } catch (e) { console.warn('[ChatWidget]', e); }
      };

      ws.onclose = function () {
        if (reconnectCount >= 3) { setStatus('Unable to connect. Please refresh.'); return; }
        reconnectCount++;
        setStatus('Disconnected — retrying…');
        sendBtn.disabled = true;
        showTyping(false);
        setTimeout(connect, 3500);
      };

      ws.onerror = function () { setStatus('Connection error'); sendBtn.disabled = true; };
    }

    function send() {
      var text = input.value.trim();
      if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
      addMessage('user', text);
      ws.send(JSON.stringify({ message: text }));
      input.value = '';
      showTyping(true);
    }

    sendBtn.addEventListener('click', send);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });
    sendBtn.disabled = true;
    connect();
  }

  if (WEBSITE_ID) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(WEBSITE_ID); });
    else init(WEBSITE_ID);
  } else {
    var baseUrl = scriptTag.src.substring(0, scriptTag.src.lastIndexOf('/static/'));
    fetch(baseUrl + '/api/websites/resolve/?api_key=' + API_KEY)
      .then(function (r) { return r.json(); })
      .then(function (data) { if (data.website_id) init(data.website_id); })
      .catch(function () { console.warn('[ChatWidget] Add data-website-id to your script tag.'); });
  }
})();