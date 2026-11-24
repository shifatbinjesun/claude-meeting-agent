// Claude Meet bridge. Injected into Claude's OWN dedicated browser profile only.
// - Replaces the microphone with an in-page audio stream that carries Claude's voice
//   (the physical microphone is never opened; camera requests are refused -> camera stays off).
// - Captures ONLY remote meeting audio (WebRTC remote tracks), downsampled to 16 kHz PCM.
// - Observes the DOM for chat messages and participants (read-only) and reports to Python.
// Nothing here bypasses sign-in, admission, host controls or Google security features.
(() => {
  if (window.__claudeBridge) return;
  const B = (window.__claudeBridge = {
    version: 1, gen: 0, captureEnabled: false, nodes: [], outEnd: 0,
    stats: { capturedFrames: 0, played: 0, flushes: 0, remoteTracks: 0, droppedStale: 0, lastPeak: 0 },
    seenMsgs: new Set(), participants: {},
  });
  let ctx = null, micDest = null, micGain = null, mixIn = null, proc = null;

  function b64FromBuf(buf) {
    const bytes = new Uint8Array(buf); let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function bufFromB64(b64) {
    const s = atob(b64); const u = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
    return u.buffer;
  }
  function ensure() {
    if (ctx) { if (ctx.state === "suspended") ctx.resume(); return ctx; }
    ctx = new AudioContext({ sampleRate: 48000 });
    micDest = ctx.createMediaStreamDestination();
    micGain = ctx.createGain(); micGain.connect(micDest);
    mixIn = ctx.createGain();
    proc = ctx.createScriptProcessor(2048, 1, 1);
    const sink = ctx.createGain(); sink.gain.value = 0;
    mixIn.connect(proc); proc.connect(sink); sink.connect(ctx.destination);
    const ratio = ctx.sampleRate / 16000;
    proc.onaudioprocess = (e) => {
      const x = e.inputBuffer.getChannelData(0);
      const n = Math.floor(x.length / ratio); const out = new Int16Array(n); let peak = 0;
      for (let i = 0; i < n; i++) {
        const a = Math.floor(i * ratio), b = Math.max(a + 1, Math.floor((i + 1) * ratio)); let s = 0;
        for (let j = a; j < b; j++) s += x[j];
        s /= (b - a); const m = Math.abs(s); if (m > peak) peak = m;
        out[i] = Math.max(-1, Math.min(1, s)) * 32767;
      }
      B.stats.lastPeak = peak;
      if (B.captureEnabled && typeof window.__claudeAudioIn === "function") {
        B.stats.capturedFrames++;
        window.__claudeAudioIn(b64FromBuf(out.buffer), peak);
      }
    };
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  B.ensure = ensure;

  function attachRemote(track) {
    try {
      ensure();
      const ms = new MediaStream([track]);
      // Chrome only feeds remote WebRTC audio into WebAudio when it is also attached to a media element.
      const el = new Audio(); el.muted = true; el.srcObject = ms; el.play().catch(() => {});
      const src = ctx.createMediaStreamSource(ms); src.connect(mixIn);
      B.stats.remoteTracks++;
      track.addEventListener("ended", () => { try { src.disconnect(); } catch (e) {} B.stats.remoteTracks--; });
    } catch (e) { console.warn("[claude] attach failed", e); }
  }

  // ---- Remote audio capture via RTCPeerConnection track events ----
  const OrigPC = window.RTCPeerConnection;
  if (OrigPC) {
    class ClaudePC extends OrigPC {
      constructor(...args) {
        super(...args);
        this.addEventListener("track", (ev) => { if (ev.track && ev.track.kind === "audio") attachRemote(ev.track); });
      }
    }
    window.RTCPeerConnection = ClaudePC;
    if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = ClaudePC;
  }

  // ---- Microphone replacement; camera refused ----
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia = async (c) => {
      if (c && c.video && !c.audio) throw new DOMException("Camera disabled for Claude", "NotAllowedError");
      if (c && c.audio) {
        ensure();
        return new MediaStream([micDest.stream.getAudioTracks()[0].clone()]);
      }
      throw new DOMException("Not allowed", "NotAllowedError");
    };
  }

  // ---- Claude's voice output ----
  B.setGen = (g) => { B.gen = g; };
  B.play = (b64, rate, gen) => {
    if (gen !== B.gen) { B.stats.droppedStale++; return -1; }
    ensure();
    const i16 = new Int16Array(bufFromB64(b64)); const f = new Float32Array(i16.length);
    for (let i = 0; i < i16.length; i++) f[i] = i16[i] / 32768;
    const buf = ctx.createBuffer(1, f.length, rate); buf.copyToChannel(f, 0);
    const src = ctx.createBufferSource(); src.buffer = buf; src.connect(micGain);
    const t = Math.max(ctx.currentTime + 0.03, B.outEnd); src.start(t); B.outEnd = t + buf.duration;
    B.nodes.push(src); src.onended = () => { B.nodes = B.nodes.filter((n) => n !== src); };
    B.stats.played++;
    return B.outEnd - ctx.currentTime;
  };
  B.flush = (newGen) => {
    if (typeof newGen === "number") B.gen = newGen;
    const t0 = performance.now();
    for (const n of B.nodes) { try { n.stop(); n.disconnect(); } catch (e) {} }
    B.nodes = []; B.outEnd = 0; B.stats.flushes++;
    return performance.now() - t0;
  };
  B.queued = () => (ctx ? Math.max(0, B.outEnd - ctx.currentTime) : 0);
  B.setCapture = (on) => { B.captureEnabled = !!on; if (on) ensure(); return B.captureEnabled; };

  // ---- Read-only DOM observation: chat + participants ----
  function text(el) { return (el && (el.innerText || el.textContent) || "").trim(); }
  B.scanChat = () => {
    const out = [];
    document.querySelectorAll("[data-message-id]").forEach((el) => {
      const id = el.getAttribute("data-message-id");
      if (!id || B.seenMsgs.has(id)) return;
      B.seenMsgs.add(id);
      const group = el.closest("[data-sender-id]") || el.parentElement?.closest("[data-sender-name]") ||
                    el.closest("[jsname]")?.parentElement;
      let sender = group?.getAttribute?.("data-sender-name") || "";
      if (!sender && group) { const s = group.querySelector("[data-sender-name], .poVWob, .YTbUzc"); sender = text(s); }
      out.push({ id, sender: sender.slice(0, 80), text: text(el).slice(0, 2000) });
    });
    return out;
  };
  B.scanParticipants = () => {
    const now = {};
    document.querySelectorAll("[data-participant-id]").forEach((el) => {
      const id = el.getAttribute("data-participant-id");
      const nameEl = el.querySelector("[data-self-name], .zWGUib, .XEazBc, .notranslate");
      const name = (nameEl && (nameEl.getAttribute("data-self-name") || text(nameEl))) || "";
      if (id && name && name.length < 80) now[id] = name.split("\n")[0];
    });
    return now;
  };
  function hasButton(rx) {
    for (const b of document.querySelectorAll("button,[role=button]")) {
      if (!b.getClientRects().length) continue;   // ignore hidden controls
      const l = (b.getAttribute("aria-label") || "") + " " + text(b);
      if (rx.test(l)) return true;
    }
    return false;
  }
  B.detect = () => {
    const body = (document.body && document.body.innerText || "").slice(0, 20000);
    return {
      url: location.href.split("?")[0],
      inCall: hasButton(/leave call|কল ছেড়ে|কল থেকে বেরিয়ে/i),
      askToJoin: hasButton(/^\s*ask to join|join now|যোগ দিতে বলুন|এখনই যোগ দিন/i),
      waiting: /asking to be let in|wait until a meeting host|someone will let you in|আপনাকে যোগ দেওয়ার অনুমতি/i.test(body),
      denied: /denied your request|can't join this (video )?call|you can.t join|আপনার অনুরোধ প্রত্যাখ্যান/i.test(body),
      removed: /you('ve| have) been removed|removed you from/i.test(body),
      ended: /you left the meeting|the call has ended|meeting has ended|call ended|return to home screen/i.test(body),
      needsSignIn: /sign in|choose an account/i.test(body) && location.hostname.startsWith("accounts."),
      remoteTracks: B.stats.remoteTracks, peak: B.stats.lastPeak, queued: B.queued(),
      chatOpen: [...document.querySelectorAll("textarea[aria-label*='message' i], textarea[aria-label*='মেসেজ']")]
        .some((t) => t.offsetParent !== null),
    };
  };
})();
