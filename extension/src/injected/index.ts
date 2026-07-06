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

(function() {
  console.log('[OpenLink] 插件已加载');

  // ── Dedup state (per conversation) ─────────────────────────────────────
  const processedByConv = new Map<string, Set<string>>();
  function getConvId(): string {
    const m = location.pathname.match(/\/(?:chat|c)\/([^/?#]+)/) ||
              location.search.match(/[?&]id=([^&]+)/);
    return m ? m[1] : '__default__';
  }
  function getProcessed(): Set<string> {
    const id = getConvId();
    if (!processedByConv.has(id)) processedByConv.set(id, new Set());
    return processedByConv.get(id)!;
  }

  // ── Core scanner: feed any text (chunk / event data) to look for <tool> tags ──
  const RE_TOOL = /<tool(?:\s[^>]*)?>[\s\S]*?<\/tool(?:_call)?>/g;

  function scanText(text: string) {
    if (!text) return;
    if (!text.includes('<tool')) return;          // fast-path skip
    let match: RegExpExecArray | null;
    while ((match = RE_TOOL.exec(text)) !== null) {
      const full = match[0];
      const processed = getProcessed();
      if (processed.has(full)) continue;
      processed.add(full);
      console.log('[OpenLink] 检测到工具调用:', full);
      const inner = full.replace(/^<tool[^>]*>|<\/tool(?:_call)?>$/g, '').trim();
      const toolCall = parseXmlToolCall(full) || tryParseToolJSON(inner);
      if (toolCall) {
        console.log('[OpenLink] 工具调用解析:', toolCall);
        window.postMessage({type: 'TOOL_CALL', data: toolCall}, '*');
      } else {
        console.warn('[OpenLink] 工具调用解析失败:', full);
      }
    }
    RE_TOOL.lastIndex = 0;
  }

  // DeepSeek streams response content as JSON-fragmented SSE chunks:
  //   data: {"p":"response/fragments/-1/content","o":"APPEND","v":"<"}
  //   data: {"v":"tool"}
  //   data: {"v":" name"}
  //   ...
  // Each `v` string is a tiny text slice. Concatenate them so the tool tag
  // regex sees `<tool name="...">...</tool>` as a single contiguous string.
  // Returns null if the body doesn't look like DeepSeek SSE (no `data:` lines).
  function reassembleSSEFragments(body: string): string | null {
    if (!body.includes('data:')) return null;
    const lines = body.split('\n');
    const parts: string[] = [];
    let foundAny = false;
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const json = line.slice(5).trim();
      if (!json || json[0] !== '{') continue;
      try {
        const obj = JSON.parse(json);
        if (!obj) continue;
        // Case 1: `v` is a string — most APPEND chunks (e.g. "tool", " name", "=\"")
        if (typeof obj.v === 'string') {
          parts.push(obj.v);
          foundAny = true;
          continue;
        }
        // Case 2: `v` is the initial state object — content lives in
        //         response.fragments[].content. Without this, the very first
        //         character of the response (often `<` when AI emits a tool
        //         tag) is dropped, breaking tool detection.
        if (obj.v && typeof obj.v === 'object' && obj.v.response && Array.isArray(obj.v.response.fragments)) {
          for (const frag of obj.v.response.fragments) {
            if (typeof frag.content === 'string') {
              parts.push(frag.content);
              foundAny = true;
            }
          }
        }
      } catch { /* not JSON, skip */ }
    }
    return foundAny ? parts.join('') : null;
  }

  // ── 1. fetch interception (streaming response body) ─────────────────────
  const originalFetch = window.fetch;
  window.fetch = function(...args: any[]) {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    console.log('[OpenLink] fetch →', url);

    let buffer = '';
    const decoder = new TextDecoder();

    return originalFetch.apply(this, args).then(async response => {
      const reader = response.body?.getReader();
      if (!reader) return response;

      const stream = new ReadableStream({
        async start(controller) {
          while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            const text = decoder.decode(value, { stream: true });
            buffer += text;
            // SSE: each chunk often contains one or more `data: ...\n\n` blocks
            scanText(text);
            controller.enqueue(value);
          }
          controller.close();
        }
      });
      return new Response(stream, {
        headers: response.headers,
        status: response.status
      });
    });
  };

  // ── 2. EventSource interception (SSE via EventSource API) ───────────────
  if (typeof window.EventSource === 'function') {
    const OriginalEventSource = window.EventSource;
    function WrappedEventSource(this: any, url: any, opts?: any) {
      console.log('[OpenLink] EventSource →', String(url));
      const es = new OriginalEventSource(url, opts);
      const origAdd = es.addEventListener.bind(es);
      es.addEventListener = function(type: string, listener: any, options?: any) {
        if (type === 'message' && typeof listener === 'function') {
          return origAdd('message', (e: MessageEvent) => {
            scanText(typeof e.data === 'string' ? e.data : String(e.data));
            listener(e);
          }, options);
        }
        return origAdd(type, listener, options);
      };
      // Also intercept the onmessage setter (sites that use property-style listeners)
      let onMsgHandler: ((e: MessageEvent) => void) | null = null;
      Object.defineProperty(es, 'onmessage', {
        get: () => onMsgHandler,
        set: (h: ((e: MessageEvent) => void) | null) => {
          onMsgHandler = h;
          origAdd('message', (e: MessageEvent) => {
            scanText(typeof e.data === 'string' ? e.data : String(e.data));
            if (h) h.call(es, e);
          });
        },
      });
      return es;
    }
    WrappedEventSource.prototype = OriginalEventSource.prototype;
    WrappedEventSource.CONST = (OriginalEventSource as any).CONST;
    // @ts-ignore — wrap constructor
    window.EventSource = WrappedEventSource as any;
  }

  // ── 3. XMLHttpRequest interception (fallback for legacy stacks) ───────
  if (typeof window.XMLHttpRequest === 'function') {
    const origOpen = XMLHttpRequest.prototype.open;
    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method: string, url: string | URL, ...rest: any[]) {
      (this as any).__openlinkUrl = String(url);
      return origOpen.apply(this, [method, url, ...rest] as any);
    };
    XMLHttpRequest.prototype.send = function(...args: any[]) {
      this.addEventListener('readystatechange', function() {
        if (this.readyState === 4) {
          const url = (this as any).__openlinkUrl || '';
          const rt = this.responseText || (typeof this.response === 'string' ? this.response : '');
          console.log('[OpenLink] XHR ←', url, 'status:', this.status, 'len:', rt.length);
          // DeepSeek streams tool calls via SSE-style JSON fragments
          // (data: {"v":"<"}, data: {"v":"tool"}, ...) — concatenate `v` strings first.
          try { scanText(rt); } catch (e) { /* ignore */ }
          try {
            const reassembled = reassembleSSEFragments(rt);
            if (reassembled !== null) {
              console.log('[OpenLink] reassembled SSE:', reassembled.length, 'chars');
              scanText(reassembled);
            }
          } catch (e) { /* ignore */ }
        }
      });
      return origSend.apply(this, args);
    };
  }

  // ── 4. WebSocket interception (last resort) ────────────────────────────
  if (typeof window.WebSocket === 'function') {
    const OriginalWebSocket = window.WebSocket;
    function WrappedWebSocket(this: any, url: any, protocols?: any) {
      console.log('[OpenLink] WebSocket →', String(url));
      const ws = new OriginalWebSocket(url, protocols);
      const origDispatch = ws.dispatchEvent.bind(ws);
      ws.dispatchEvent = function(event: Event) {
        if (event && (event as any).type === 'message') {
          const e = event as MessageEvent;
          const data = typeof e.data === 'string' ? e.data : '';
          if (data) scanText(data);
        }
        return origDispatch(event);
      };
      return ws;
    }
    WrappedWebSocket.prototype = OriginalWebSocket.prototype;
    WrappedWebSocket.CONST = (OriginalWebSocket as any).CONST;
    // @ts-ignore
    window.WebSocket = WrappedWebSocket as any;
  }
})();