function parseOptions(raw: unknown): string[] {
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') { try { return JSON.parse(raw); } catch { return []; } }
  return [];
}

function getNativeSetter() {
  return Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
}

function parseXmlToolCall(raw: string): any | null {
  // DeepSeek sometimes emits tool tags with JSON-escaped quotes (\") in the
  // raw SSE body — normalize first so the regex sees plain ASCII quotes.
  const s = raw.replace(/\\"/g, '"');
  const nameMatch = s.match(/^<tool\s+name="([^"]+)"(?:\s+call_id="([^"]+)")?/);
  if (!nameMatch) return null;
  const name = nameMatch[1];
  const callId = nameMatch[2] || null;
  const args: Record<string, string> = {};
  const paramRe = /<parameter\s+name="([^"]+)">([\s\S]*?)<\/parameter>/g;
  let m;
  while ((m = paramRe.exec(s)) !== null) args[m[1]] = m[2];
  return { name, args, callId };
}

function tryParseToolJSON(raw: string): any | null {
  try { return JSON.parse(raw); } catch {}
  try {
    let result = '';
    let inString = false;
    let escaped = false;
    for (let i = 0; i < raw.length; i++) {
      const ch = raw[i];
      if (escaped) { result += ch; escaped = false; continue; }
      if (ch === '\\') { result += ch; escaped = true; continue; }
      if (ch === '"') {
        if (!inString) { inString = true; result += ch; continue; }
        let j = i + 1;
        while (j < raw.length && raw[j] === ' ') j++;
        const next = raw[j];
        if (next === ':' || next === ',' || next === '}' || next === ']') {
          inString = false; result += ch;
        } else {
          result += '\\"';
        }
        continue;
      }
      result += ch;
    }
    return JSON.parse(result);
  } catch {}
  return null;
}

type FillMethod = 'paste' | 'execCommand' | 'value' | 'prosemirror';

interface SiteConfig {
  editor: string;
  sendBtn: string;
  stopBtn: string | null;
  fillMethod: FillMethod;
  useObserver: boolean;
  responseSelector?: string;
}

function getSiteConfig(): SiteConfig {
  const h = location.hostname;
  if (h.includes('gemini.google.com'))
    return { editor: 'div.ql-editor[contenteditable="true"]', sendBtn: 'button.send-button[aria-label*="发送"], button.send-button[aria-label*="Send"]', stopBtn: null, fillMethod: 'execCommand', useObserver: true, responseSelector: 'model-response, .model-response-text, message-content' };
  if (h.includes('chatgpt.com'))
    return { editor: '.ProseMirror[contenteditable="true"]#prompt-textarea, .ProseMirror[contenteditable="true"]', sendBtn: 'button[data-testid="send-button"], button[aria-label*="Send"], button[aria-label*="发送"]', stopBtn: null, fillMethod: 'prosemirror', useObserver: true, responseSelector: '.markdown.prose' };
  if (h.includes('x.com') || h.includes('grok.com'))
    return { editor: 'textarea[aria-label="Ask Grok anything"], textarea[placeholder="Ask anything"], textarea', sendBtn: 'button[aria-label="Submit"], button.send-button', stopBtn: null, fillMethod: 'value', useObserver: false };
  if (h.includes('kimi.com'))
    return { editor: '.chat-input-editor[contenteditable="true"], div[contenteditable="true"][data-lexical-editor="true"]', sendBtn: '.send-button, button[aria-label*="Send"]', stopBtn: null, fillMethod: 'execCommand', useObserver: false };
  if (h.includes('chat.mistral.ai'))
    return { editor: 'div.ProseMirror[contenteditable="true"]', sendBtn: '.ms-auto .flex.gap-2 button[type="submit"], button.bg-state-primary', stopBtn: null, fillMethod: 'execCommand', useObserver: false };
  if (h.includes('perplexity.ai'))
    return { editor: '#ask-input[contenteditable="true"], div[contenteditable="true"][data-lexical-editor="true"]', sendBtn: 'button[aria-label="Submit"], button[aria-label="Send"]', stopBtn: null, fillMethod: 'execCommand', useObserver: false };
  if (h.includes('openrouter.ai'))
    return { editor: 'textarea[data-testid="composer-input"], textarea[placeholder="Start a new message..."]', sendBtn: 'button[data-testid="send-button"], button[aria-label="Send message"]', stopBtn: null, fillMethod: 'value', useObserver: false };
  if (h.includes('qwen.ai'))
    return { editor: 'textarea.message-input-textarea, #chat-input', sendBtn: 'button.omni-button-content-btn, div.message-input-right-button-send button', stopBtn: null, fillMethod: 'value', useObserver: true, responseSelector: '.chat-response-message' };
  if (h.includes('t3.chat'))
    return { editor: 'textarea#chat-input, textarea[placeholder*="Type your message"]', sendBtn: 'button[type="submit"], button[aria-label*="Send"]', stopBtn: null, fillMethod: 'value', useObserver: false };
  if (h.includes('aistudio.google.com'))
    return { editor: 'textarea[placeholder*="Start typing a prompt"]', sendBtn: 'button.ctrl-enter-submits.ms-button-primary[type="submit"], button[aria-label*="Run"]', stopBtn: null, fillMethod: 'value', useObserver: true, responseSelector: 'ms-chat-turn' };
  if (h.includes('github.com'))
    return { editor: '#copilot-chat-textarea, textarea[placeholder*="How can I help"]', sendBtn: 'button[aria-labelledby*="Send"], button:has(.octicon-paper-airplane)', stopBtn: null, fillMethod: 'value', useObserver: false };
  if (h.includes('z.ai'))
    return { editor: '#chat-input', sendBtn: '#send-message-button', stopBtn: null, fillMethod: 'value', useObserver: false };
  if (h.includes('arena.ai'))
    return { editor: 'textarea[name="message"], textarea[placeholder="Ask followup…"]', sendBtn: 'button[type="submit"]', stopBtn: null, fillMethod: 'value', useObserver: true, responseSelector: '.prose' };
  if (h.includes('deepseek.com'))
    // DeepSeek chat (verified 2026-07): plain <textarea> + semantic BEM-style button classes
    // (ds-button--primary/--filled/--circle). Earlier Slate.js + CSS-Modules selectors are stale.
    //
    // Detection path: useObserver=false → injected.js fetch interception extracts <tool> tags
    // from streaming API responses. To switch to DOM observer in the future, the response
    // container is `div.ds-message > div.ds-markdown.ds-assistant-message-main-content`
    // (outer list-item wrappers like ._4f9bf79._43c05b5 are CSS-Modules hashes that change
    // per deploy — stick to the semantic `.ds-assistant-message-main-content` selector).
    return {
      editor: 'textarea[placeholder="Message DeepSeek"], textarea[name="search"], textarea',
      // filled-circle primary button (distinct from upload which is capsule-small).
      // Note: ds-button--disabled does not reliably toggle between empty/non-empty
      // textarea states (DeepSeek controls clickability via JS state, not the class).
      // Drop the :not filter — fillAndSend's 50×100ms polling + Enter-key fallback
      // at line ~725 covers edge cases where click() fires on a genuinely inert button.
      sendBtn: '.ds-button--primary.ds-button--filled.ds-button--circle',
      // Same element swaps icon to a stop glyph during streaming.
      stopBtn: '.ds-button--primary.ds-button--filled.ds-button--circle',
      fillMethod: 'value',
      useObserver: false,
    };
  // Default: empty selectors — safe no-op for any unmatched host.
  return { editor: '', sendBtn: '', stopBtn: null, fillMethod: 'value', useObserver: false };
}

if (!(window as any).__OPENLINK_LOADED__) {
  (window as any).__OPENLINK_LOADED__ = true;

  const cfg = getSiteConfig();

  if (!cfg.useObserver) {
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('injected.js');
    (document.head || document.documentElement).appendChild(script);
  } else if (cfg.responseSelector) {
    const sel = cfg.responseSelector;
    if (document.body) startDOMObserver(sel);
    else document.addEventListener('DOMContentLoaded', () => startDOMObserver(sel));
  }

  let execQueue = Promise.resolve();
  window.addEventListener('message', (event) => {
    if (event.data.type === 'TOOL_CALL') {
      execQueue = execQueue.then(() => executeToolCall(event.data.data));
    }
  });

  if (document.body) injectSettingsButton();
  else document.addEventListener('DOMContentLoaded', injectSettingsButton);

  function mountInputListener() {
    const editorEl = querySelectorFirst(cfg.editor);
    if (editorEl) {
      attachInputListener(editorEl as HTMLElement);
    } else {
      const obs = new MutationObserver(() => {
        const el = querySelectorFirst(cfg.editor);
        if (el) { obs.disconnect(); attachInputListener(el as HTMLElement); }
      });
      obs.observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.body) mountInputListener();
  else document.addEventListener('DOMContentLoaded', mountInputListener);
}

function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = Math.imul(31, h) + s.charCodeAt(i) | 0;
  return h >>> 0;
}

// ── Shared autoExecute flag (module-level so executeToolCall can read it) ──
// Default true to match original behavior (always auto-execute on first run).
// Read at startup, kept live via chrome.storage.onChanged so toggling the
// setting in the floating ⚙️ dialog takes effect without reload.
let autoExecute = true;
chrome.storage.local.get(['autoExecute']).then(r => {
  if (r.autoExecute !== undefined) autoExecute = !!r.autoExecute;
});
chrome.storage.onChanged.addListener((changes) => {
  if ('autoExecute' in changes) autoExecute = !!changes.autoExecute.newValue;
});

// Flip to true to see verbose logs (initial-prompt GET, etc.).
// The `工具调用*` / `提取到工具调用` logs stay on regardless — real signals.
const DEBUG = false;
const debugLog = (...args: any[]) => { if (DEBUG) console.log('[OpenLink]', ...args); };

function getConversationId(): string {
  const m = location.pathname.match(/\/chat\/([^/?#]+)/) || location.search.match(/[?&]id=([^&]+)/);
  return m ? m[1] : '__default__';
}

function isExecuted(key: string): boolean {
  try {
    const store: Record<string, number> = JSON.parse(localStorage.getItem('openlink_executed') || '{}');
    return !!store[key];
  } catch { return false; }
}

const TTL = 7 * 24 * 60 * 60 * 1000;

function markExecuted(key: string): void {
  try {
    const store: Record<string, number> = JSON.parse(localStorage.getItem('openlink_executed') || '{}');
    const now = Date.now();
    for (const k of Object.keys(store)) {
      if (now - store[k] > TTL) delete store[k];
    }
    store[key] = now;
    localStorage.setItem('openlink_executed', JSON.stringify(store));
  } catch {}
}

async function executeToolCallRaw(toolCall: any): Promise<string> {
  const { authToken, apiUrl } = await chrome.storage.local.get(['authToken', 'apiUrl']);
  if (!apiUrl) return '请先在插件中配置 API 地址';
  const headers: any = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  const response = await bgFetch(`${apiUrl}/exec`, { method: 'POST', headers, body: JSON.stringify(toolCall) });
  if (response.status === 401) return '认证失败，请在插件中重新输入 Token';
  if (!response.ok) return `[OpenLink 错误] HTTP ${response.status}`;
  const result = JSON.parse(response.body);
  return result.output || result.error || '[OpenLink] 空响应';
}

function renderToolCard(data: any, _full: string, sourceEl: Element, key: string, processed: Set<string>) {
  // Find stable anchor: message-content's parent, which Angular doesn't rebuild
  const messageContent = sourceEl.closest('message-content') ?? sourceEl.closest('.prose') ?? sourceEl;
  const anchor = messageContent.parentElement ?? sourceEl.parentElement;
  if (!anchor) return;

  // Prevent duplicate cards
  if (anchor.querySelector(`[data-openlink-key="${key}"]`)) return;

  const args = data.args || {};
  const card = document.createElement('div');
  card.setAttribute('data-openlink-key', key);
  card.style.cssText = 'border:1px solid #444;border-radius:8px;padding:12px;margin:8px 0;background:#1e1e2e;color:#cdd6f4;font-size:13px';

  const header = document.createElement('div');
  header.style.cssText = 'font-weight:bold;margin-bottom:8px';
  header.innerHTML = `🔧 ${data.name} <span style="color:#888;font-size:11px">#${data.callId || ''}</span>`;
  card.appendChild(header);

  const argsBox = document.createElement('div');
  argsBox.style.cssText = 'margin:8px 0;background:#181825;border-radius:6px;padding:8px';
  for (const [k, v] of Object.entries(args)) {
    const row = document.createElement('div');
    row.style.cssText = 'margin-bottom:4px';
    row.innerHTML = `<span style="color:#89b4fa;font-size:11px">${k}</span>`;
    const val = document.createElement('div');
    val.style.cssText = 'color:#cdd6f4;font-size:12px;font-family:monospace;white-space:pre-wrap;max-height:80px;overflow-y:auto';
    val.textContent = typeof v === 'string' ? v : JSON.stringify(v);
    row.appendChild(val);
    argsBox.appendChild(row);
  }
  card.appendChild(argsBox);

  const btnRow = document.createElement('div');
  btnRow.style.cssText = 'display:flex;gap:8px';
  const execBtn = document.createElement('button');
  execBtn.textContent = '执行';
  execBtn.style.cssText = 'padding:4px 12px;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px';
  const skipBtn = document.createElement('button');
  skipBtn.textContent = '忽略';
  skipBtn.style.cssText = 'padding:4px 12px;background:#313244;color:#cdd6f4;border:1px solid #45475a;border-radius:6px;cursor:pointer;font-size:12px';
  btnRow.appendChild(execBtn);
  btnRow.appendChild(skipBtn);
  card.appendChild(btnRow);

  execBtn.onclick = async () => {
    execBtn.disabled = true;
    execBtn.textContent = '执行中...';
    markExecuted(key);
    try {
      const text = await executeToolCallRaw(data);
      const resultBox = document.createElement('div');
      resultBox.style.cssText = 'margin-top:10px;background:#181825;border-radius:6px;padding:8px;max-height:200px;overflow-y:auto;font-family:monospace;font-size:12px;color:#cdd6f4;white-space:pre-wrap';
      resultBox.textContent = text;
      const insertBtn = document.createElement('button');
      insertBtn.textContent = '插入到对话';
      insertBtn.style.cssText = 'margin-top:6px;padding:4px 12px;background:#313244;color:#89b4fa;border:1px solid #89b4fa;border-radius:6px;cursor:pointer;font-size:12px';
      insertBtn.onclick = () => fillAndSend(text, true);
      card.appendChild(resultBox);
      card.appendChild(insertBtn);
      execBtn.textContent = '✅ 已执行';
    } catch {
      execBtn.textContent = '❌ 执行失败';
      execBtn.disabled = false;
    }
  };

  skipBtn.onclick = () => { card.remove(); processed.delete(key); };

  anchor.insertBefore(card, messageContent);
}

function startDOMObserver(_responseSelector: string) {
  const processed = new Set<string>();
  const TOOL_RE = /<tool(?:\s[^>]*)?>[\s\S]*?<\/tool>/g;
  // autoExecute state is shared at module scope (declared above) so both
  // DOM observer path and the injected.js → TOOL_CALL → executeToolCall
  // path honor the same setting.

  function scanText(text: string, sourceEl?: Element) {
    if (!text.includes('<tool')) return;
    TOOL_RE.lastIndex = 0;
    let match;
    while ((match = TOOL_RE.exec(text)) !== null) {
      const full = match[0];
      const inner = full.replace(/^<tool[^>]*>|<\/tool>$/g, '').trim();
      const data = parseXmlToolCall(full) || tryParseToolJSON(inner);
      if (!data) { console.warn('[OpenLink] 工具调用解析失败:', full); continue; }
      const convId = getConversationId();
      const key = data.callId ? `${convId}:${data.name}:${data.callId}` : String(hashStr(full));
      if (processed.has(key)) continue;
      console.log('[OpenLink] 提取到工具调用:', data);

      if (sourceEl) {
        processed.add(key);
        renderToolCard(data, full, sourceEl, key, processed);
        if (autoExecute && !isExecuted(key)) {
          markExecuted(key);
          window.postMessage({ type: 'TOOL_CALL', data }, '*');
        }
      } else {
        if (isExecuted(key)) continue;
        processed.add(key);
        markExecuted(key);
        window.postMessage({ type: 'TOOL_CALL', data }, '*');
      }
    }
  }

  function scanNode(node: Node) {
    let el: Element | null;
    if (node.nodeType === Node.TEXT_NODE) {
      el = (node as Text).parentElement;
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      el = node as Element;
    } else {
      return;
    }
    if (!el) return;
    const mc = findResponseContainer(el);
    if (mc) scheduleScan(mc);
  }

  function findResponseContainer(el: Element | null): Element | null {
    while (el) {
      const tag = el.tagName.toLowerCase();
      if (tag === 'message-content') return el;
      if (tag === 'ms-chat-turn') return el;
      if (el.classList.contains('chat-response-message')) return el;
      if (el.classList.contains('prose')) return el;
      el = el.parentElement;
    }
    return null;
  }

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  let maxWaitTimer: ReturnType<typeof setTimeout> | null = null;
  const pendingContainers = new Set<Element>();

  // 块级标签：遍历到这些元素时在前面插入换行
  const BLOCK_TAGS = new Set(['P', 'DIV', 'BR', 'LI', 'TR', 'PRE', 'BLOCKQUOTE', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6']);

  // 跳过这些元素及其子树（UI 噪声）
  const SKIP_TAGS = new Set(['MS-THOUGHT-CHUNK', 'MAT-ICON', 'SCRIPT', 'STYLE', 'BUTTON', 'MAT-EXPANSION-PANEL-HEADER']);

  function extractText(node: Node, buf: string[]): void {
    if (node.nodeType === Node.TEXT_NODE) {
      buf.push(node.textContent || '');
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const el = node as Element;

    // 跳过 aria-hidden 元素（Material Icons 图标文字）和噪声标签
    if (el.getAttribute('aria-hidden') === 'true') return;
    if (SKIP_TAGS.has(el.tagName)) return;

    // 块级元素前插换行，保证多行结构
    if (BLOCK_TAGS.has(el.tagName)) buf.push('\n');

    for (const child of el.childNodes) {
      extractText(child, buf);
    }
  }

  function getCleanText(el: Element): string {
    const buf: string[] = [];
    extractText(el, buf);
    return buf.join('');
  }

  function scheduleScan(container: Element) {
    pendingContainers.add(container);
    if (!maxWaitTimer) {
      maxWaitTimer = setTimeout(() => {
        maxWaitTimer = null;
        if (debounceTimer) { clearTimeout(debounceTimer); debounceTimer = null; }
        const els = [...pendingContainers];
        pendingContainers.clear();
        requestAnimationFrame(() => {
          for (const el of els) scanText(getCleanText(el), el);
        });
      }, 3000);
    }
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      if (maxWaitTimer) { clearTimeout(maxWaitTimer); maxWaitTimer = null; }
      const els = [...pendingContainers];
      pendingContainers.clear();
      requestAnimationFrame(() => {
        for (const el of els) scanText(getCleanText(el), el);
      });
    }, 800);
  }

  new MutationObserver(mutations => {
    for (const mutation of mutations) {
      if (mutation.type === 'characterData') {
        const container = findResponseContainer((mutation.target as Text).parentElement);
        if (container) scheduleScan(container);
      } else {
        mutation.addedNodes.forEach(scanNode);
      }
    }
  }).observe(document.body, { childList: true, subtree: true, characterData: true });

  // Initial scan for already-rendered tool calls (e.g. after page refresh)
  requestAnimationFrame(() => {
    document.querySelectorAll('message-content, .chat-response-message, ms-chat-turn').forEach(el => {
      scanText(getCleanText(el), el);
    });
  });
}

// ── Edge-snapping FAB with auto-collapse ──────────────────────────────
// The settings button is draggable. On release, if it's close enough to
// a screen edge, it snaps there and after a short delay auto-collapses
// to a half-circle peeking from the edge (icon only). Hovering it
// re-expands it back to the full pill. Position + collapsed state are
// persisted in chrome.storage so they survive page refresh.
const SETTINGS_BTN_KEY = 'openlink-settings-btn';
const BTN_W = 100;             // pill width when expanded (icon + text "OpenLink设置")
const BTN_H = 36;
const PEEK = 18;              // half-circle visible when collapsed (matches radius)
const SNAP_THRESHOLD = 60;    // px from edge → snap & collapse
const COLLAPSE_DELAY = 800;   // ms after snap before collapsing
const UNCOLLAPSE_DELAY = 250; // ms after mouseleave before re-collapsing

interface BtnPos { x: number; y: number; edge: 'left' | 'right' | 'top' | 'bottom' | null; collapsed: boolean }

function injectSettingsButton() {
  // Remove any pre-existing button (handles reinstalls / duplicate injections)
  document.getElementById('openlink-buttons')?.remove();

  // Inject stylesheet once — defines expanded pill, collapsed circle, transitions.
  if (!document.getElementById('openlink-settings-btn-style')) {
    const s = document.createElement('style');
    s.id = 'openlink-settings-btn-style';
    s.textContent = `
      #openlink-buttons {
        position: fixed !important;
        z-index: 99999;
        min-width: ${BTN_H}px; width: auto; height: ${BTN_H}px;
        padding: 0 14px; box-sizing: border-box;
        background: #1677ff; color: #fff;
        border: none; border-radius: 18px;
        cursor: grab; font-size: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        user-select: none; -webkit-user-select: none;
        display: inline-flex; align-items: center; justify-content: center; gap: 6px;
        white-space: nowrap; overflow: hidden;
        transition: width 0.22s cubic-bezier(0.4,0,0.2,1),
                    border-radius 0.22s,
                    padding 0.22s,
                    left 0.18s, top 0.18s;
      }
      #openlink-buttons.dragging { cursor: grabbing; transition: none; }
      #openlink-buttons .ol-icon { font-size: 14px; line-height: 1; display: inline-block; }
      #openlink-buttons .ol-text { display: inline-block; }
      #openlink-buttons.collapsed {
        width: ${BTN_H}px; padding: 0;
        border-radius: 50%;
      }
      #openlink-buttons.collapsed .ol-text { display: none; }
    `;
    document.head.appendChild(s);
  }

  const btn = document.createElement('button');
  btn.id = 'openlink-buttons';
  btn.innerHTML = '<span class="ol-icon">🔗</span><span class="ol-text">OpenLink设置</span>';
  btn.title = 'OpenLink 设置';

  document.body.appendChild(btn);

  // pos.x / pos.y = left-top corner of the BUTTON's bounding box. Auto-sized
  // width means we measure the actual pill width after insertion — every snap
  // / collapse calculation uses pillW so the math stays correct even if the
  // text or icon changes later.
  const pillW = btn.offsetWidth || BTN_W;

  const pos: BtnPos = {
    x: window.innerWidth - pillW - 20,
    y: window.innerHeight - BTN_H - 80,
    edge: null,
    collapsed: false,
  };
  let dragOrigin: { x: number; y: number; bx: number; by: number } | null = null;
  let snapTimer: any = null;
  let uncollTimer: any = null;
  let dragMoved = false;

  const save = () => chrome.storage.local.set({ [SETTINGS_BTN_KEY]: pos });

  function applyPos() {
    btn.style.left = pos.x + 'px';
    btn.style.top = pos.y + 'px';
  }

  // ── Position helpers ──
  function setExpandedPosOnEdge(edge: 'left' | 'right' | 'top' | 'bottom') {
    // Fully visible position when expanded and snapped to that edge.
    if (edge === 'left')   pos.x = 0;
    else if (edge === 'right')  pos.x = window.innerWidth - pillW;
    else if (edge === 'top')    pos.y = 0;
    else                        pos.y = window.innerHeight - BTN_H;
  }
  function setCollapsedPosOnEdge(edge: 'left' | 'right' | 'top' | 'bottom') {
    // Only PEEK pixels visible. Button hangs off-screen so visible portion
    // looks like a half-circle bump.
    if (edge === 'right')  pos.x = window.innerWidth - PEEK;
    else if (edge === 'left')   pos.x = -(BTN_H - PEEK);
    else if (edge === 'top')    pos.y = -(BTN_H - PEEK);
    else                        pos.y = window.innerHeight - PEEK;
  }
  function setEdge(edge: 'left' | 'right' | 'top' | 'bottom') {
    pos.edge = edge;
  }

  function collapse() {
    if (!pos.edge) return;
    setCollapsedPosOnEdge(pos.edge);
    pos.collapsed = true;
    btn.classList.add('collapsed');
    applyPos();
    save();
  }

  function expand() {
    if (!pos.collapsed || !pos.edge) return;
    pos.collapsed = false;
    btn.classList.remove('collapsed');
    setExpandedPosOnEdge(pos.edge);
    applyPos();
    save();
  }

  // ── Load saved state ──
  chrome.storage.local.get([SETTINGS_BTN_KEY]).then((cfg) => {
    const saved: BtnPos | undefined = cfg[SETTINGS_BTN_KEY];
    if (!saved) { applyPos(); return; }
    pos.x = saved.x;
    pos.y = saved.y;
    pos.edge = saved.edge;
    pos.collapsed = !!saved.collapsed;
    if (pos.collapsed && pos.edge) {
      btn.classList.add('collapsed');
      // re-snap position in case viewport changed since save
      setCollapsedPosOnEdge(pos.edge);
    }
    applyPos();
  });

  // ── Drag ──
  btn.addEventListener('mousedown', (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragOrigin = { x: e.clientX, y: e.clientY, bx: pos.x, by: pos.y };
    dragMoved = false;
    btn.classList.add('dragging');
    clearTimeout(snapTimer);
    // expand immediately on grab
    if (pos.collapsed) expand();
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragOrigin) return;
    const dx = e.clientX - dragOrigin.x;
    const dy = e.clientY - dragOrigin.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) dragMoved = true;
    pos.x = dragOrigin.bx + dx;
    pos.y = dragOrigin.by + dy;
    // Clamp so the pill (always expanded during drag) keeps at least a
    // full 36px height visible on the chosen edge.
    pos.x = Math.max(-(pillW - BTN_H), Math.min(window.innerWidth - BTN_H, pos.x));
    pos.y = Math.max(0, Math.min(window.innerHeight - BTN_H, pos.y));
    pos.edge = null;             // dragging clears any snapped edge
    btn.classList.remove('collapsed');
    applyPos();
  });

  document.addEventListener('mouseup', () => {
    if (!dragOrigin) return;
    dragOrigin = null;
    btn.classList.remove('dragging');

    // Distance to each edge of the CURRENT (expanded) pill.
    const distLeft   = pos.x;
    const distRight  = window.innerWidth - pos.x - pillW;
    const distTop    = pos.y;
    const distBottom = window.innerHeight - pos.y - BTN_H;
    const minDist = Math.min(distLeft, distRight, distTop, distBottom);

    // Only collapse if the user dropped it RIGHT NEAR an edge. Middle-of-screen
    // drops stay where they were — they never trigger pos.edge / collapse.
    if (minDist < SNAP_THRESHOLD) {
      const edge: 'left' | 'right' | 'top' | 'bottom' =
        (minDist === distLeft)   ? 'left'
      : (minDist === distRight)  ? 'right'
      : (minDist === distTop)    ? 'top' : 'bottom';
      setEdge(edge);
      setExpandedPosOnEdge(edge);
      applyPos();
      save();
      // Schedule collapse unless the user is already hovering the button.
      clearTimeout(snapTimer);
      snapTimer = setTimeout(() => {
        if (!btn.matches(':hover') && !dragOrigin) collapse();
      }, COLLAPSE_DELAY);
    } else {
      // In the middle: clear snap state, keep expanded, no auto-collapse.
      pos.edge = null;
      pos.collapsed = false;
      btn.classList.remove('collapsed');
      save();
    }
  });

  // ── Hover (collapsed → expand, leave → re-collapse) ──
  btn.addEventListener('mouseenter', () => {
    clearTimeout(uncollTimer);
    if (pos.collapsed) expand();
  });
  btn.addEventListener('mouseleave', () => {
    clearTimeout(uncollTimer);
    uncollTimer = setTimeout(() => {
      if (pos.edge && !dragOrigin && pos.collapsed) collapse();
    }, UNCOLLAPSE_DELAY);
  });

  // ── Click → settings dialog (only if not a drag) ──
  btn.addEventListener('click', (e) => {
    if (dragMoved) { dragMoved = false; return; }
    if (pos.collapsed) expand();
    showSettingsDialog();
  });
}

async function bgFetch(url: string, options?: any): Promise<{ ok: boolean; status: number; body: string }> {
  try {
    if (!chrome.runtime?.id) {
      return { ok: false, status: -1, body: '请刷新页面后重试（扩展刚刚被更新）' };
    }
    return await chrome.runtime.sendMessage({ type: 'FETCH', url, options });
  } catch (e: any) {
    const msg = String(e?.message || e);
    if (msg.includes('Extension context invalidated') || msg.includes('Receiving end does not exist')) {
      return { ok: false, status: -1, body: '请刷新页面后重试（扩展刚刚被更新）' };
    }
    throw e;
  }
}

async function sendInitPrompt() {
  const { authToken, apiUrl } = await chrome.storage.local.get(['authToken', 'apiUrl']);
  if (!apiUrl) { showSettingsDialog(); return; }

  // Show user what URL we're about to call, for diagnosis
  const requestUrl = `${apiUrl}/prompt`;
  debugLog('[OpenLink] GET', requestUrl, 'token:', authToken ? `${authToken.slice(0, 8)}...(${authToken.length})` : '(none)');

  const headers: any = { 'Content-Type': 'application/json' };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  const resp = await bgFetch(requestUrl, { headers });
  if (!resp.ok) { alert(`获取初始化提示词失败\nURL: ${requestUrl}\n状态: ${resp.status}\n响应: ${resp.body?.slice(0, 200) || '(空)'}`); return; }

  if (location.hostname.includes('aistudio.google.com')) {
    await fillAiStudioSystemInstructions(resp.body);
    return;
  }

  fillAndSend(resp.body, true);
}

/** Lightweight settings dialog — opened when extension has no API URL configured. */
function showSettingsDialog() {
  if (document.getElementById('openlink-settings-dialog')) return;

  const overlay = document.createElement('div');
  overlay.id = 'openlink-settings-dialog';
  // Transparent full-screen overlay — no visual shadow, but still modal
  // because it intercepts mouse clicks on the page below. Click on the
  // overlay (i.e. outside the dialog box) closes the dialog.
  overlay.style.cssText = [
    'position:fixed', 'inset:0', 'z-index:999999',
    'display:flex', 'align-items:center', 'justify-content:center',
    'font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif',
  ].join(';');

  overlay.innerHTML = `
    <div id="openlink-settings-box" style="background:#1e1e1e;color:#e1e3ec;padding:24px;border-radius:12px;width:480px;max-width:90%;min-width:360px;min-height:280px;box-shadow:0 8px 32px rgba(0,0,0,0.5);position:relative;overflow:hidden">
      <!-- 8 resize handles: 4 corners + 4 edges. innerHTML-injected as children. -->
      <div data-resize-handle="nw" style="position:absolute;left:0;top:0;width:14px;height:14px;cursor:nwse-resize;z-index:1"></div>
      <div data-resize-handle="n"  style="position:absolute;left:14px;top:0;right:14px;height:8px;cursor:ns-resize;z-index:1"></div>
      <div data-resize-handle="ne" style="position:absolute;right:0;top:0;width:14px;height:14px;cursor:nesw-resize;z-index:1"></div>
      <div data-resize-handle="w"  style="position:absolute;left:0;top:14px;bottom:14px;width:8px;cursor:ew-resize;z-index:1"></div>
      <div data-resize-handle="e"  style="position:absolute;right:0;top:14px;bottom:14px;width:8px;cursor:ew-resize;z-index:1"></div>
      <div data-resize-handle="sw" style="position:absolute;left:0;bottom:0;width:14px;height:14px;cursor:nesw-resize;z-index:1"></div>
      <div data-resize-handle="s"  style="position:absolute;left:14px;bottom:0;right:14px;height:8px;cursor:ns-resize;z-index:1"></div>
      <div data-resize-handle="se" style="position:absolute;right:0;bottom:0;width:14px;height:14px;cursor:nwse-resize;z-index:1"></div>
      <div id="openlink-settings-header" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;cursor:grab;user-select:none">
        <h2 style="margin:0;font-size:18px;">OpenLink 设置</h2>
        <button id="openlink-settings-close" title="关闭" aria-label="关闭" style="padding:0;width:24px;height:24px;background:transparent;color:#9aa0a8;border:none;border-radius:4px;cursor:pointer;font-size:18px;line-height:1;display:flex;align-items:center;justify-content:center;">×</button>
      </div>
      <div id="openlink-settings-tabs" style="display:flex;gap:0;margin-bottom:16px;border-bottom:1px solid #2a2d3a">
        <button class="openlink-tab openlink-tab-active" data-tab="settings" style="padding:8px 16px;background:transparent;color:#fff;border:none;border-bottom:2px solid #1677ff;cursor:pointer;font-size:13px;font-weight:500;margin-bottom:-1px">设置</button>
        <button class="openlink-tab" data-tab="tool" style="padding:8px 16px;background:transparent;color:#9aa0a8;border:none;border-bottom:2px solid transparent;cursor:pointer;font-size:13px;font-weight:500;margin-bottom:-1px">工具命令</button>
      </div>

      <div class="openlink-panel" data-panel="settings" style="display:block">
        <label style="display:block;margin-bottom:12px;font-size:13px;color:#9aa0a8;">
          API 地址
          <input id="openlink-url" type="text" placeholder="http://127.0.0.1:39527"
            style="display:block;width:100%;margin-top:4px;padding:8px 10px;background:#0f1117;color:#e1e3ec;border:1px solid #2a2d3a;border-radius:6px;font-family:monospace;font-size:13px;box-sizing:border-box">
        </label>
        <label style="display:block;margin-bottom:16px;font-size:13px;color:#9aa0a8;">
          Token
          <input id="openlink-token" type="password" placeholder="token"
            style="display:block;width:100%;margin-top:4px;padding:8px 10px;background:#0f1117;color:#e1e3ec;border:1px solid #2a2d3a;border-radius:6px;font-family:monospace;font-size:13px;box-sizing:border-box">
        </label>
        <label style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:13px;color:#9aa0a8;cursor:pointer;">
          <input id="openlink-auto-execute" type="checkbox" style="margin:0;">
          自动执行工具调用（无需手动点 "执行"）
        </label>
        <label style="display:flex;align-items:center;gap:8px;margin-bottom:4px;font-size:13px;color:#9aa0a8;cursor:pointer;">
          <input id="openlink-auto-send" type="checkbox" style="margin:0;">
          自动提交（取消勾选则填入 AI 输入框后需手动点发送）
        </label>
        <label style="display:block;margin-bottom:16px;font-size:13px;color:#9aa0a8;">
          自动提交延迟区间 (秒)
          <div style="display:flex;gap:8px;margin-top:4px;">
            <input id="openlink-delay-min" type="number" step="0.1" min="0" placeholder="最小 (x)"
              style="flex:1;padding:8px 10px;background:#0f1117;color:#e1e3ec;border:1px solid #2a2d3a;border-radius:6px;font-family:monospace;font-size:13px;box-sizing:border-box">
            <input id="openlink-delay-max" type="number" step="0.1" min="0" placeholder="最大 (y)"
              style="flex:1;padding:8px 10px;background:#0f1117;color:#e1e3ec;border:1px solid #2a2d3a;border-radius:6px;font-family:monospace;font-size:13px;box-sizing:border-box">
          </div>
          <div style="margin-top:4px;font-size:11px;color:#6b7280;">每次触发时在 x 与 y 之间随机取一个秒数</div>
        </label>
        <div style="display:flex;gap:8px;justify-content:space-between;align-items:center">
          <button id="openlink-cancel" style="padding:8px 16px;background:transparent;color:#e1e3ec;border:1px solid #2a2d3a;border-radius:6px;cursor:pointer;">取消</button>
          <div style="display:flex;gap:8px;">
            <button id="openlink-save" style="padding:8px 16px;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;">保存</button>
            <button id="openlink-init-from-dialog" title="先保存当前设置, 再向 AI 发送系统提示词" style="padding:8px 16px;background:#1e1e2e;color:#cdd6f4;border:1px solid #45475a;border-radius:6px;cursor:pointer;font-size:13px;">初始化</button>
          </div>
        </div>
      </div>

      <div class="openlink-panel" data-panel="tool" style="display:none">
        <div style="font-size:13px;color:#9aa0a8;margin-bottom:6px">在下方输入或粘贴工具调用 XML，提交后直接 POST <code style="font-size:12px">/exec</code>，结果回显在下方。</div>
        <div style="display:flex;gap:8px;align-items:flex-start">
          <div style="display:flex;flex-direction:column;gap:6px;flex:0 0 50px">
            <button id="openlink-tool-execute" style="width:50px;height:50px;padding:0;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center">执行</button>
            <button id="openlink-tool-clear" style="width:50px;height:50px;padding:0;background:transparent;color:#9aa0a8;border:1px solid #2a2d3a;border-radius:6px;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center">清空</button>
          </div>
          <textarea id="openlink-tool-input" placeholder='&lt;tool name="list_dir"&gt;\n  &lt;parameter name="path"&gt;.&lt;/parameter&gt;\n&lt;/tool&gt;'
            style="flex:1;height:166px;padding:8px 10px;background:#0f1117;color:#e1e3ec;border:1px solid #2a2d3a;border-radius:6px;font-family:monospace;font-size:12px;box-sizing:border-box;outline:none"></textarea>
        </div>
        <div id="openlink-tool-result-wrap" style="display:none;margin-top:12px">
          <div style="font-size:11px;color:#6b7280;margin-bottom:4px">结果：</div>
          <div style="display:flex;gap:8px;align-items:flex-start">
            <div style="display:flex;flex-direction:column;gap:6px;flex:0 0 50px">
              <button id="openlink-tool-insert" style="width:50px;height:50px;padding:0;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center">插入</button>
              <button id="openlink-tool-copy" style="width:50px;height:50px;padding:0;background:transparent;color:#cdd6f4;border:1px solid #45475a;border-radius:6px;cursor:pointer;font-size:12px;display:flex;align-items:center;justify-content:center">复制</button>
            </div>
            <pre id="openlink-tool-result" style="flex:1;margin:0;padding:10px;background:#0f1117;border:1px solid #2a2d3a;border-radius:6px;font-family:monospace;font-size:12px;white-space:pre-wrap;max-height:106px;overflow-y:auto;color:#cdd6f4;min-height:106px;box-sizing:border-box"></pre>
          </div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Pre-fill from existing storage
  chrome.storage.local.get(['authToken', 'apiUrl', 'autoExecute', 'autoSend', 'delayMin', 'delayMax']).then((cfg: any) => {
    (document.getElementById('openlink-url') as HTMLInputElement).value = cfg.apiUrl || '';
    (document.getElementById('openlink-token') as HTMLInputElement).value = cfg.authToken || '';
    (document.getElementById('openlink-auto-execute') as HTMLInputElement).checked = cfg.autoExecute !== false;
    (document.getElementById('openlink-auto-send') as HTMLInputElement).checked = cfg.autoSend !== false;
    (document.getElementById('openlink-delay-min') as HTMLInputElement).value = cfg.delayMin != null ? String(cfg.delayMin) : '1';
    (document.getElementById('openlink-delay-max') as HTMLInputElement).value = cfg.delayMax != null ? String(cfg.delayMax) : '4';
  });

  const close = () => overlay.remove();

  // ── Make the dialog draggable from the header bar ──
  // mousedown on header → record offset; mousemove on document → translate
  // the box. mouseup ends the drag. CSS handles no-select during drag.
  const box = document.getElementById('openlink-settings-box') as HTMLElement;
  const header = document.getElementById('openlink-settings-header') as HTMLElement;
  const MIN_W = 360, MIN_H = 280;
  const SETTINGS_SIZE_KEY = 'openlink-settings-dialog-size';

  // Restore previously-saved width/height
  chrome.storage.local.get([SETTINGS_SIZE_KEY]).then((cfg) => {
    const sz = cfg[SETTINGS_SIZE_KEY];
    if (sz && sz.w >= MIN_W && sz.h >= MIN_H) {
      box.style.width  = sz.w + 'px';
      box.style.height = sz.h + 'px';
    }
  });

  let dragOffsetX = 0, dragOffsetY = 0, dragging = false;
  header.addEventListener('mousedown', (e) => {
    if ((e.target as HTMLElement).id === 'openlink-settings-close') return;
    dragging = true;
    const rect = box.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    // Switch from centered flex layout to absolute positioning at the cursor spot
    box.style.position = 'fixed';
    box.style.left = `${rect.left}px`;
    box.style.top = `${rect.top}px`;
    box.style.margin = '0';
    box.style.transform = 'none';
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    box.style.left = `${e.clientX - dragOffsetX}px`;
    box.style.top = `${e.clientY - dragOffsetY}px`;
  });
  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.userSelect = '';
  });

  // ── 8-direction resize (4 edges + 4 corners) ──
  // mousedown on a handle → record start rect + which direction; mousemove
  // adjusts width/height/x/y; mouseup persists to chrome.storage.
  type ResizeDir = 'nw' | 'n' | 'ne' | 'w' | 'e' | 'sw' | 's' | 'se';
  let resizeDir: ResizeDir | null = null;
  let resizeStartRect: { left: number; top: number; width: number; height: number } | null = null;
  let resizeStartX = 0, resizeStartY = 0;

  overlay.querySelectorAll<HTMLElement>('[data-resize-handle]').forEach((handle) => {
    handle.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      resizeDir = handle.dataset.resizeHandle as ResizeDir;
      const rect = box.getBoundingClientRect();
      resizeStartRect = { left: rect.left, top: rect.top, width: rect.width, height: rect.height };
      resizeStartX = e.clientX;
      resizeStartY = e.clientY;
      // Promote to fixed if not already (so resize works after drag too)
      if (box.style.position !== 'fixed') {
        box.style.position = 'fixed';
        box.style.left = rect.left + 'px';
        box.style.top = rect.top + 'px';
        box.style.margin = '0';
        box.style.transform = 'none';
      }
      document.body.style.userSelect = 'none';
    });
  });

  document.addEventListener('mousemove', (e) => {
    if (!resizeDir || !resizeStartRect) return;
    const dx = e.clientX - resizeStartX;
    const dy = e.clientY - resizeStartY;
    let { left, top, width, height } = resizeStartRect;

    // Width — west edges grow/shrink width AND shift left
    if (resizeDir === 'nw' || resizeDir === 'w' || resizeDir === 'sw') {
      const w = Math.max(MIN_W, width - dx);
      left = left + (width - w);
      width = w;
    } else if (resizeDir === 'ne' || resizeDir === 'e' || resizeDir === 'se') {
      width = Math.max(MIN_W, width + dx);
    }
    // Height — north edges grow/shrink height AND shift top
    if (resizeDir === 'nw' || resizeDir === 'n' || resizeDir === 'ne') {
      const h = Math.max(MIN_H, height - dy);
      top = top + (height - h);
      height = h;
    } else if (resizeDir === 'sw' || resizeDir === 's' || resizeDir === 'se') {
      height = Math.max(MIN_H, height + dy);
    }

    // Clamp inside viewport
    width = Math.min(width, window.innerWidth - left);
    height = Math.min(height, window.innerHeight - top);
    if (left < 0) { width -= -left; left = 0; }
    if (top < 0)  { height -= -top; top = 0; }

    box.style.left   = left   + 'px';
    box.style.top    = top    + 'px';
    box.style.width  = width  + 'px';
    box.style.height = height + 'px';
  });

  document.addEventListener('mouseup', () => {
    if (!resizeDir || !resizeStartRect) return;
    resizeDir = null;
    resizeStartRect = null;
    document.body.style.userSelect = '';
    // Persist final size
    const rect = box.getBoundingClientRect();
    chrome.storage.local.set({
      [SETTINGS_SIZE_KEY]: { w: Math.round(rect.width), h: Math.round(rect.height) },
    });
  });

  // ── Click on the transparent overlay (i.e. outside the dialog box) closes it ──
  overlay.addEventListener('mousedown', (e) => {
    if (e.target === overlay) close();
  });

  document.getElementById('openlink-settings-close')!.addEventListener('click', close);
  document.getElementById('openlink-cancel')!.addEventListener('click', close);
  // "🔗 初始化" from inside the settings dialog — same action as the
  // floating 🔗 button (send system prompt to AI). Closes the dialog first
  // so the user sees the prompt being filled/sent into the editor cleanly.
  document.getElementById('openlink-init-from-dialog')!.addEventListener('click', async () => {
    const ok = await saveSettings();
    if (!ok) return;  // validation failed, dialog stays open
    close();
    sendInitPrompt();
  });
  document.getElementById('openlink-save')!.addEventListener('click', async () => {
    const ok = await saveSettings();
    if (!ok) return;
    close();
  });

  // ── Tab switching ──
  overlay.querySelectorAll<HTMLButtonElement>('.openlink-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      overlay.querySelectorAll<HTMLButtonElement>('.openlink-tab').forEach((t) => {
        const active = t === tab;
        t.classList.toggle('openlink-tab-active', active);
        (t as HTMLElement).style.color = active ? '#fff' : '#9aa0a8';
        (t as HTMLElement).style.borderBottomColor = active ? '#1677ff' : 'transparent';
      });
      overlay.querySelectorAll<HTMLElement>('.openlink-panel').forEach((p) => {
        p.style.display = p.dataset.panel === target ? 'block' : 'none';
      });
    });
  });

  // ── Tool command panel ──
  // Parse the XML the user typed, then POST /exec directly (bypassing the
  // auto-fill-AI-editor flow). Result is rendered into the dialog.
  document.getElementById('openlink-tool-execute')!.addEventListener('click', async () => {
    const raw = (document.getElementById('openlink-tool-input') as HTMLTextAreaElement).value.trim();
    const resultBox = document.getElementById('openlink-tool-result')!;
    const resultWrap = document.getElementById('openlink-tool-result-wrap')!;
    const execBtn = document.getElementById('openlink-tool-execute') as HTMLButtonElement;
    if (!raw) {
      resultWrap.style.display = 'block';
      resultBox.textContent = '⚠ 请输入工具调用 XML';
      resultBox.style.color = '#fbbf24';
      return;
    }
    execBtn.disabled = true;
    execBtn.textContent = '执行中...';
    try {
      // normalize \" → " so pasted-from-source XML parses
      const normalized = raw.replace(/\\"/g, '"');
      const toolCall = parseXmlToolCall(normalized);
      if (!toolCall) {
        resultWrap.style.display = 'block';
        resultBox.textContent = '⚠ 无法解析工具调用 XML，请检查格式\n\n原始输入：\n' + raw;
        resultBox.style.color = '#fbbf24';
        return;
      }
      const result = await executeToolCallRaw(toolCall);
      resultWrap.style.display = 'block';
      resultBox.style.color = result.startsWith('[OpenLink') || result.includes('错误') ? '#f87171' : '#a6e3a1';
      resultBox.textContent = result;
    } finally {
      execBtn.disabled = false;
      execBtn.textContent = '执行';
    }
  });
  document.getElementById('openlink-tool-clear')!.addEventListener('click', () => {
    (document.getElementById('openlink-tool-input') as HTMLTextAreaElement).value = '';
    document.getElementById('openlink-tool-result-wrap')!.style.display = 'none';
  });

  // ── 复制 / 插入 工具结果 ──
  // 复制: 把执行结果文本拷到剪贴板 (用 navigator.clipboard, 失败回退 execCommand).
  // 插入: 把结果当消息发到 AI 编辑器, autoSend=false (用户手动点发送).
  async function copyResultToClipboard(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      showToast('✅ 已复制');
    } catch (e) {
      // Fallback: select + execCommand
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); showToast('✅ 已复制'); } catch {}
      document.body.removeChild(ta);
    }
  }

  document.getElementById('openlink-tool-copy')!.addEventListener('click', () => {
    const resultText = document.getElementById('openlink-tool-result')!.textContent || '';
    if (!resultText.trim()) { showToast('⚠ 无结果可复制'); return; }
    copyResultToClipboard(resultText);
  });

  document.getElementById('openlink-tool-insert')!.addEventListener('click', async () => {
    const resultText = document.getElementById('openlink-tool-result')!.textContent || '';
    if (!resultText.trim()) { showToast('⚠ 无结果可插入'); return; }
    // AutoExecute 决定是否自动提交 (跟主流程行为对齐):
    //   勾选 → fill + 自动发送 (autoSend=true, 走 delayMin~delayMax 随机延迟)
    //   不勾选 → 只填入编辑框, 用户自己点发送 (autoSend=false)
    const { autoExecute } = await chrome.storage.local.get(['autoExecute']);
    const autoSubmit = autoExecute !== false;  // 默认 true (跟主流程一致)
    fillAndSend(resultText, autoSubmit);
    showToast(autoSubmit ? '✅ 已插入并自动提交' : '✅ 已插入到 AI 输入框');
  });

  // Shared save logic — returns true on success, false on validation failure.
  // Used by both the [保存] and [初始化] buttons (后者先保存再触发 init).
  async function saveSettings(): Promise<boolean> {
    let url = (document.getElementById('openlink-url') as HTMLInputElement).value.trim();
    const token = (document.getElementById('openlink-token') as HTMLInputElement).value.trim();
    // Strip trailing slash to avoid double-slash in requests
    while (url.endsWith('/')) url = url.slice(0, -1);
    const urlChanged = url.length > 0;
    const tokenChanged = token.length > 0;
    if (urlChanged && !tokenChanged) {
      alert('请填写 Token\n\nToken 来自：\n  C:\\Users\\UryWu\\.openlink\\settings.json\n\n打开那个文件，复制 "token" 字段的值');
      return false;
    }

    // ── New-settings validation (independent of /auth probe) ──
    const autoExec = (document.getElementById('openlink-auto-execute') as HTMLInputElement).checked;
    const autoSendCb = (document.getElementById('openlink-auto-send') as HTMLInputElement).checked;
    const minRaw = (document.getElementById('openlink-delay-min') as HTMLInputElement).value.trim();
    const maxRaw = (document.getElementById('openlink-delay-max') as HTMLInputElement).value.trim();
    const minN = Number(minRaw);
    const maxN = Number(maxRaw);
    if (minRaw === '' || maxRaw === '' || Number.isNaN(minN) || Number.isNaN(maxN)) {
      alert('延迟区间不合法：请填写数字'); return false;
    }
    if (minN < 0) { alert('最小延迟不能小于 0'); return false; }
    if (maxN > 60) { alert('最大延迟不能超过 60 秒（避免 UI 被长时间阻塞）'); return false; }
    if (maxN < minN) { alert('最大延迟必须 ≥ 最小延迟'); return false; }

    const saveBtn = document.getElementById('openlink-save') as HTMLButtonElement;

    // ── Token verification (only when URL or Token actually changed) ──
    if (urlChanged || tokenChanged) {
      saveBtn.disabled = true;
      saveBtn.textContent = '验证中...';
      try {
        const probe = await bgFetch(`${url}/auth`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!probe.ok || !probe.body?.includes('"valid":true')) {
          alert(`Token 验证失败\n\n后端响应: ${probe.body?.slice(0, 200) || `状态 ${probe.status}`}\n\n请检查：\n1. 后端是否在运行\n2. Token 是不是当前 settings.json 里的值\n3. API 地址末尾不要带 /`);
          saveBtn.disabled = false;
          saveBtn.textContent = '保存';
          return false;
        }
      } catch (e: any) {
        alert('连接后端失败：' + (e?.message || e));
        saveBtn.disabled = false;
        saveBtn.textContent = '保存';
        return false;
      }
    }

    // ── Persist (only overwrite URL/Token if the user actually typed them) ──
    const updates: Record<string, any> = {
      autoExecute: autoExec,
      autoSend: autoSendCb,
      delayMin: minN,
      delayMax: maxN,
    };
    if (urlChanged) updates.apiUrl = url;
    if (tokenChanged) updates.authToken = token;

    await new Promise<void>((resolve) => {
      chrome.storage.local.set(updates, () => resolve());
    });
    saveBtn.disabled = false;
    saveBtn.textContent = '保存';
    return true;
  }
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
}

async function fillAiStudioSystemInstructions(prompt: string) {
  const openBtn = document.querySelector<HTMLElement>('button[data-test-system-instructions-card]');
  if (!openBtn) { fillAndSend(prompt, true); return; }

  openBtn.click();
  await new Promise(r => setTimeout(r, 600));

  const textarea = document.querySelector<HTMLTextAreaElement>('textarea[aria-label="System instructions"]');
  if (!textarea) { fillAndSend(prompt, true); return; }

  const nativeSetter = getNativeSetter();
  if (nativeSetter) nativeSetter.call(textarea, prompt);
  else textarea.value = prompt;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));

  await new Promise(r => setTimeout(r, 300));

  const closeBtn = document.querySelector<HTMLElement>('button[data-test-close-button]');
  if (closeBtn) closeBtn.click();
}

function showQuestionPopup(question: string, options: string[]): Promise<string> {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:2147483647;display:flex;align-items:center;justify-content:center';
    const box = document.createElement('div');
    box.style.cssText = 'background:#1e1e2e;color:#cdd6f4;border-radius:12px;padding:24px;max-width:480px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.5)';
    const title = document.createElement('p');
    title.style.cssText = 'margin:0 0 16px;font-size:15px;line-height:1.5;white-space:pre-wrap';
    title.textContent = question;
    box.appendChild(title);
    options.forEach((opt, i) => {
      const btn = document.createElement('button');
      btn.textContent = `${i + 1}. ${opt}`;
      btn.style.cssText = 'display:block;width:100%;margin-bottom:8px;padding:10px 14px;background:#313244;color:#cdd6f4;border:1px solid #45475a;border-radius:8px;cursor:pointer;font-size:13px;text-align:left';
      btn.onmouseenter = () => { btn.style.background = '#45475a'; };
      btn.onmouseleave = () => { btn.style.background = '#313244'; };
      btn.onclick = () => { overlay.remove(); resolve(opt); };
      box.appendChild(btn);
    });
    overlay.appendChild(box);
    document.body.appendChild(overlay);
  });
}

// Inline approval card for tool calls when autoExecute is OFF.
// Inserts a non-modal card directly under the AI message that produced the
// tool call (no full-screen overlay, doesn't block clicking elsewhere).
// Resolves with the user's decision so the caller can proceed or bail.
function showToolApprovalPopup(toolCall: any): Promise<'execute' | 'ignore'> {
  return new Promise(resolve => {
    // Find the wrapper that holds the latest assistant message + its toolbar.
    // DeepSeek structure: div._4f9bf79 > [.ds-message, .ds-flex(toolbar)]
    // The wrapper has class _4f9bf79; check for assistant content inside.
    const wrappers = document.querySelectorAll('[class*="_4f9bf79"]');
    let targetWrapper: Element | null = null;
    for (let i = wrappers.length - 1; i >= 0; i--) {
      if (wrappers[i].querySelector('.ds-assistant-message-main-content')) {
        targetWrapper = wrappers[i];
        break;
      }
    }

    const buildCard = () => {
      const card = document.createElement('div');
      card.setAttribute('data-openlink-approval', 'true');
      card.style.cssText = 'margin:8px 12px 12px;padding:12px 14px;border:1px solid #45475a;border-radius:8px;background:#1e1e2e;color:#cdd6f4;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;display:flex;flex-direction:column;gap:10px';

      const header = document.createElement('div');
      header.style.cssText = 'display:flex;align-items:center;gap:10px;flex-wrap:wrap';
      const titleEl = document.createElement('span');
      titleEl.style.cssText = 'color:#89b4fa;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;font-size:13px';
      titleEl.textContent = '🔧 openlink 检测到工具调用（自动执行已关闭）';
      header.appendChild(titleEl);
      const nameEl = document.createElement('span');
      nameEl.style.cssText = 'padding:3px 8px;background:#181825;border-radius:4px;color:#a6e3a1;font-size:12px';
      nameEl.textContent = `${toolCall.name}${toolCall.callId ? ' #' + toolCall.callId : ''}`;
      header.appendChild(nameEl);
      card.appendChild(header);

      if (toolCall.args && Object.keys(toolCall.args).length > 0) {
        const argsEl = document.createElement('pre');
        argsEl.style.cssText = 'margin:0;padding:8px 10px;background:#181825;border-radius:6px;font-size:12px;max-height:140px;overflow-y:auto;white-space:pre-wrap;color:#cdd6f4;font-family:inherit';
        argsEl.textContent = JSON.stringify(toolCall.args, null, 2);
        card.appendChild(argsEl);
      }

      const btnRow = document.createElement('div');
      btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end';
      const ignoreBtn = document.createElement('button');
      ignoreBtn.textContent = '忽略';
      ignoreBtn.style.cssText = 'padding:6px 14px;background:transparent;color:#cdd6f4;border:1px solid #45475a;border-radius:6px;cursor:pointer;font-size:13px';
      const execBtn = document.createElement('button');
      execBtn.textContent = '执行';
      execBtn.style.cssText = 'padding:6px 14px;background:#1677ff;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:500';
      btnRow.appendChild(ignoreBtn);
      btnRow.appendChild(execBtn);
      card.appendChild(btnRow);

      execBtn.onclick = () => { card.remove(); resolve('execute'); };
      ignoreBtn.onclick = () => { card.remove(); resolve('ignore'); };
      return card;
    };

    if (targetWrapper) {
      // Anchor inside the AI message wrapper, after the toolbar.
      targetWrapper.appendChild(buildCard());
    } else {
      // Fallback: float at top-right (no modal, no backdrop, no click-blocking).
      const float = document.createElement('div');
      float.style.cssText = 'position:fixed;top:80px;right:20px;z-index:99999;width:380px;max-width:90vw';
      const card = buildCard();
      // Wrap click handlers so removing the float also fires the resolve.
      const origExec = card.querySelectorAll('button')[1]?.onclick;
      const origIgn = card.querySelectorAll('button')[0]?.onclick;
      card.querySelectorAll('button')[1]!.onclick = (e) => { float.remove(); if (origExec) (origExec as any)(e); };
      card.querySelectorAll('button')[0]!.onclick = (e) => { float.remove(); if (origIgn) (origIgn as any)(e); };
      float.appendChild(card);
      document.body.appendChild(float);
    }
  });
}

async function executeToolCall(toolCall: any) {
  // When autoExecute is off, surface the tool call as an approval popup so
  // the user can manually trigger or skip it. Default to execute when on.
  if (!autoExecute) {
    const decision = await showToolApprovalPopup(toolCall);
    if (decision !== 'execute') {
      console.log('[OpenLink] autoExecute 关闭, 用户选择忽略:', toolCall.name);
      return;
    }
  }

  if (toolCall.name === 'question') {
    const q: string = toolCall.args?.question ?? '';
    const rawOpts = toolCall.args?.options;
    const opts: string[] = parseOptions(rawOpts);
    const answer = opts.length > 0 ? await showQuestionPopup(q, opts) : (prompt(q) ?? '');
    fillAndSend(answer, false);
    return;
  }

  try {
    const { authToken, apiUrl } = await chrome.storage.local.get(['authToken', 'apiUrl']);
    const headers: any = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

    if (!apiUrl) { fillAndSend('请先在插件中配置 API 地址', false); return; }

    const response = await bgFetch(`${apiUrl}/exec`, {
      method: 'POST',
      headers,
      body: JSON.stringify(toolCall)
    });

    if (response.status === 401) { fillAndSend('认证失败，请在插件中重新输入 Token', false); return; }
    if (!response.ok) { fillAndSend(`[OpenLink 错误] HTTP ${response.status}`, false); return; }

    const result = JSON.parse(response.body);
    const text = result.output || result.error || '[OpenLink] 空响应';

    if (result.stopStream) {
      clickStopButton();
      showToast('✅ 文件已写入成功，已停止生成');
      await new Promise(r => setTimeout(r, 600));
      fillAndSend(text, true);
      return;
    }

    fillAndSend(text, true);
  } catch (error) {
    fillAndSend(`[OpenLink 错误] ${error}`, false);
  }
}

function showToast(msg: string, durationMs = 3000): void {
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed;bottom:170px;right:20px;z-index:2147483647;background:#1e1e2e;color:#a6e3a1;border:1px solid #a6e3a1;border-radius:10px;padding:10px 16px;font-size:13px;box-shadow:0 4px 16px rgba(0,0,0,0.4)';
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), durationMs);
}

function clickStopButton(): void {
  const stopSel = getSiteConfig().stopBtn;
  if (!stopSel) return;
  const btn = document.querySelector(stopSel) as HTMLElement;
  if (btn) btn.click();
}

function showCountdownToast(ms: number, onFire: () => void): void {
  const toast = document.createElement('div');
  toast.style.cssText = 'position:fixed;bottom:130px;right:20px;z-index:2147483647;background:#1e1e2e;color:#cdd6f4;border:1px solid #45475a;border-radius:10px;padding:10px 14px;font-size:13px;display:flex;align-items:center;gap:10px;box-shadow:0 4px 16px rgba(0,0,0,0.4)';
  const label = document.createElement('span');
  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = '取消';
  cancelBtn.style.cssText = 'background:#313244;color:#f38ba8;border:1px solid #f38ba8;border-radius:6px;padding:2px 8px;cursor:pointer;font-size:12px';
  toast.appendChild(label);
  toast.appendChild(cancelBtn);
  document.body.appendChild(toast);

  let remaining = Math.ceil(ms / 1000);
  let cancelled = false;
  label.textContent = `${remaining}s 后自动提交`;
  const interval = setInterval(() => {
    remaining--;
    label.textContent = `${remaining}s 后自动提交`;
    if (remaining <= 0) { clearInterval(interval); toast.remove(); if (!cancelled) onFire(); }
  }, 1000);
  cancelBtn.onclick = () => { cancelled = true; clearInterval(interval); toast.remove(); };
}

function querySelectorFirst(selectors: string): HTMLElement | null {
  for (const sel of selectors.split(',').map(s => s.trim())) {
    const el = document.querySelector(sel) as HTMLElement | null;
    if (el) return el;
  }
  return null;
}

async function fillAndSend(result: string, autoSend = false) {
  const { editor: editorSel, sendBtn: sendBtnSel, fillMethod } = getSiteConfig();
  const editor = querySelectorFirst(editorSel);
  if (!editor) return;

  editor.focus();

  if (fillMethod === 'paste') {
    const dataTransfer = new DataTransfer();
    dataTransfer.setData('text/plain', result);
    editor.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dataTransfer, bubbles: true, cancelable: true }));
  } else if (fillMethod === 'execCommand') {
    document.execCommand('insertText', false, result);
  } else if (fillMethod === 'value') {
    const ta = editor as HTMLTextAreaElement;
    const nativeInputValueSetter = getNativeSetter();
    const current = ta.value;
    const next = current ? current + '\n' + result : result;
    if (nativeInputValueSetter) nativeInputValueSetter.call(ta, next);
    else ta.value = next;
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  } else if (fillMethod === 'prosemirror') {
    const current = editor.innerText.trim();
    editor.innerHTML = current ? current + '\n' + result : result;
    editor.dispatchEvent(new Event('input', { bubbles: true }));
    editor.dispatchEvent(new Event('change', { bubbles: true }));
  }

  if (autoSend) {
    const cfg = await chrome.storage.local.get(['autoSend', 'delayMin', 'delayMax']);
    if (cfg.autoSend === false) return;

    const min = (cfg.delayMin ?? 1) * 1000;
    const max = (cfg.delayMax ?? 4) * 1000;
    const delay = Math.random() * (max - min) + min;

    showCountdownToast(delay, () => {
      const checkAndClick = (attempts = 0) => {
        if (attempts > 50) {
          const ed = querySelectorFirst(editorSel);
          if (ed) ed.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
          return;
        }
        const sendBtn = querySelectorFirst(sendBtnSel);
        if (sendBtn) {
          sendBtn.click();
        } else {
          setTimeout(() => checkAndClick(attempts + 1), 100);
        }
      };
      checkAndClick();
    });
  }
}

// ── 斜杠命令 / @ 文件补全 ──────────────────────────────────────────────────────

let skillsCache: Array<{ name: string; description: string }> | null = null;
let skillsCacheTime = 0;
const filesCache = new Map<string, { ts: number; files: string[] }>();
const FILES_TTL = 5000;

async function fetchSkills(): Promise<Array<{ name: string; description: string }>> {
  if (skillsCache && Date.now() - skillsCacheTime < 30000) return skillsCache;
  const { authToken, apiUrl } = await chrome.storage.local.get(['authToken', 'apiUrl']);
  if (!apiUrl) return [];
  const headers: any = {};
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  try {
    const resp = await bgFetch(`${apiUrl}/skills`, { headers });
    if (!resp.ok) return [];
    const data = JSON.parse(resp.body);
    skillsCache = data.skills || [];
    skillsCacheTime = Date.now();
    return skillsCache!;
  } catch { return []; }
}

async function fetchFiles(q: string): Promise<string[]> {
  const cached = filesCache.get(q);
  if (cached && Date.now() - cached.ts < FILES_TTL) return cached.files;
  const { authToken, apiUrl } = await chrome.storage.local.get(['authToken', 'apiUrl']);
  if (!apiUrl) return [];
  const headers: any = {};
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  try {
    const resp = await bgFetch(`${apiUrl}/files?q=${encodeURIComponent(q)}`, { headers });
    if (!resp.ok) return [];
    const data = JSON.parse(resp.body);
    const files = data.files || [];
    filesCache.set(q, { ts: Date.now(), files });
    return files;
  } catch { return []; }
}

function showPickerPopup(
  anchorEl: HTMLElement,
  items: Array<{ label: string; sub?: string; value: string }>,
  onSelect: (value: string) => void,
  onDismiss: () => void
): () => void {
  const popup = document.createElement('div');
  popup.style.cssText = 'position:fixed;z-index:2147483647;background:#1e1e2e;border:1px solid #45475a;border-radius:8px;padding:4px;min-width:240px;max-width:400px;max-height:240px;overflow-y:auto;box-shadow:0 4px 16px rgba(0,0,0,0.5)';

  let activeIdx = 0;
  const rows: HTMLElement[] = [];

  function render() {
    popup.innerHTML = '';
    rows.length = 0;
    if (items.length === 0) {
      const empty = document.createElement('div');
      empty.style.cssText = 'padding:8px 12px;color:#6c7086;font-size:12px';
      empty.textContent = '无匹配项';
      popup.appendChild(empty);
      return;
    }
    items.forEach((item, i) => {
      const row = document.createElement('div');
      row.style.cssText = `padding:6px 12px;border-radius:6px;cursor:pointer;display:flex;flex-direction:column;gap:2px;background:${i === activeIdx ? '#313244' : 'transparent'}`;
      const label = document.createElement('span');
      label.style.cssText = 'color:#cdd6f4;font-size:13px';
      label.textContent = item.label;
      row.appendChild(label);
      if (item.sub) {
        const sub = document.createElement('span');
        sub.style.cssText = 'color:#6c7086;font-size:11px';
        sub.textContent = item.sub;
        row.appendChild(sub);
      }
      row.onmouseenter = () => { setActive(i); };
      row.onclick = () => { onSelect(item.value); destroy(); };
      rows.push(row);
      popup.appendChild(row);
    });
  }

  function setActive(i: number) {
    if (rows[activeIdx]) rows[activeIdx].style.background = 'transparent';
    activeIdx = i;
    if (rows[activeIdx]) {
      rows[activeIdx].style.background = '#313244';
      rows[activeIdx].scrollIntoView({ block: 'nearest' });
    }
  }

  function reposition() {
    const rect = anchorEl.getBoundingClientRect();
    const popupH = Math.min(240, popup.scrollHeight || 240);
    const spaceAbove = rect.top - 6;
    const spaceBelow = window.innerHeight - rect.bottom - 6;
    if (spaceAbove >= popupH || spaceAbove >= spaceBelow) {
      popup.style.top = `${Math.max(4, rect.top - popupH - 6)}px`;
    } else {
      popup.style.top = `${rect.bottom + 6}px`;
    }
    popup.style.left = `${rect.left}px`;
    popup.style.width = `${Math.min(400, rect.width)}px`;
  }

  render();
  document.body.appendChild(popup);
  reposition();

  function onKeyDown(e: KeyboardEvent) {
    if (!items.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); setActive((activeIdx + 1) % items.length); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); setActive((activeIdx - 1 + items.length) % items.length); }
    else if (e.key === 'Enter') { e.preventDefault(); e.stopPropagation(); onSelect(items[activeIdx].value); destroy(); }
    else if (e.key === 'Escape') { onDismiss(); destroy(); }
  }

  function onMouseDown(e: MouseEvent) {
    if (!popup.contains(e.target as Node)) { onDismiss(); destroy(); }
  }

  document.addEventListener('keydown', onKeyDown, true);
  document.addEventListener('mousedown', onMouseDown, true);
  window.addEventListener('scroll', reposition, true);
  window.addEventListener('resize', reposition);

  function destroy() {
    popup.remove();
    document.removeEventListener('keydown', onKeyDown, true);
    document.removeEventListener('mousedown', onMouseDown, true);
    window.removeEventListener('scroll', reposition, true);
    window.removeEventListener('resize', reposition);
  }

  return destroy;
}

function getEditorText(el: HTMLElement): string {
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
    return (el as HTMLTextAreaElement).value;
  }
  return el.innerText || '';
}

function getCaretPosition(el: HTMLElement): number {
  if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
    return (el as HTMLTextAreaElement).selectionStart ?? 0;
  }
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return 0;
  const range = sel.getRangeAt(0).cloneRange();
  range.selectNodeContents(el);
  range.setEnd(sel.getRangeAt(0).endContainer, sel.getRangeAt(0).endOffset);
  return range.toString().length;
}

function replaceTokenInEditor(el: HTMLElement, token: string, replacement: string, fillMethod: string) {
  if (fillMethod === 'value') {
    const ta = el as HTMLTextAreaElement;
    const val = ta.value;
    const pos = ta.selectionStart ?? val.length;
    const before = val.slice(0, pos);
    const after = val.slice(pos);
    const tokenStart = before.lastIndexOf(token);
    if (tokenStart === -1) return;
    const newVal = val.slice(0, tokenStart) + replacement + after;
    const nativeSetter = getNativeSetter();
    if (nativeSetter) nativeSetter.call(ta, newVal);
    else ta.value = newVal;
    const newCaret = tokenStart + replacement.length;
    ta.setSelectionRange(newCaret, newCaret);
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  } else if (fillMethod === 'execCommand' || fillMethod === 'prosemirror') {
    // prosemirror 也通过 execCommand insertText 拦截，不能直接写 innerHTML
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    const text = getEditorText(el);
    const pos = getCaretPosition(el);
    const before = text.slice(0, pos);
    const tokenStart = before.lastIndexOf(token);
    if (tokenStart === -1) return;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let charCount = 0;
    let startNode: Text | null = null, startOffset = 0;
    let endNode: Text | null = null, endOffset = 0;
    while (walker.nextNode()) {
      const node = walker.currentNode as Text;
      const len = node.textContent?.length ?? 0;
      if (!startNode && charCount + len > tokenStart) {
        startNode = node;
        startOffset = tokenStart - charCount;
      }
      if (startNode && !endNode && charCount + len >= tokenStart + token.length) {
        endNode = node;
        endOffset = tokenStart + token.length - charCount;
        break;
      }
      charCount += len;
    }
    if (startNode && endNode) {
      range.setStart(startNode, startOffset);
      range.setEnd(endNode, endOffset);
      sel.removeAllRanges();
      sel.addRange(range);
      document.execCommand('insertText', false, replacement);
    }
  } else {
    // paste fallback (DeepSeek/Slate)：先删除 token，再粘贴
    const ta = el as HTMLTextAreaElement;
    const val = ta.tagName === 'TEXTAREA' ? ta.value : el.innerText;
    const tokenStart = val.lastIndexOf(token);
    if (tokenStart !== -1 && ta.tagName === 'TEXTAREA') {
      const newVal = val.slice(0, tokenStart) + val.slice(tokenStart + token.length);
      const nativeSetter = getNativeSetter();
      if (nativeSetter) nativeSetter.call(ta, newVal);
      else ta.value = newVal;
      ta.setSelectionRange(tokenStart, tokenStart);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }
    const dataTransfer = new DataTransfer();
    dataTransfer.setData('text/plain', replacement);
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dataTransfer, bubbles: true, cancelable: true }));
  }
}

function attachInputListener(editorEl: HTMLElement) {
  const { fillMethod } = getSiteConfig();
  let destroyPicker: (() => void) | null = null;
  let inputVersion = 0;

  function dismiss() {
    if (destroyPicker) { destroyPicker(); destroyPicker = null; }
  }

  editorEl.addEventListener('input', async () => {
    const currentVersion = ++inputVersion;
    const text = getEditorText(editorEl);
    const pos = getCaretPosition(editorEl);
    const before = text.slice(0, pos);

    const slashMatch = before.match(/(?:^|[\s\n\u00a0])(\/([\w-]*))$/);
    if (slashMatch) {
      const token = slashMatch[1];
      const query = slashMatch[2].toLowerCase();
      const skills = await fetchSkills();
      if (currentVersion !== inputVersion) return;
      const filtered = query
        ? skills.filter(s => s.name.toLowerCase().includes(query) || s.description.toLowerCase().includes(query))
        : skills;
      dismiss();
      if (filtered.length === 0) return;
      destroyPicker = showPickerPopup(
        editorEl,
        filtered.map(s => ({
          label: s.name,
          sub: s.description,
          value: `<tool name="skill">\n  <parameter name="skill">${s.name}</parameter>\n</tool>`,
        })),
        (xml) => { replaceTokenInEditor(editorEl, token, xml, fillMethod); dismiss(); },
        dismiss
      );
      return;
    }

    const atMatch = before.match(/@([^\s]*)$/);
    if (atMatch) {
      const token = atMatch[0];
      const query = atMatch[1];
      const files = await fetchFiles(query);
      if (currentVersion !== inputVersion) return;
      dismiss();
      if (files.length === 0) return;
      destroyPicker = showPickerPopup(
        editorEl,
        files.map(f => ({ label: f, value: f })),
        (path) => { replaceTokenInEditor(editorEl, token, path, fillMethod); dismiss(); },
        dismiss
      );
      return;
    }

    dismiss();
  });
}

