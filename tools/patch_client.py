#!/usr/bin/env python3
"""Patch bundled client.html per BUILDER_HANDOFF.md."""

from __future__ import annotations

import base64
import gzip
import json
import re
from pathlib import Path

CLIENT = Path(__file__).resolve().parent.parent / "client.html"

UI_UUID = "85b84a65-4906-4bda-a0c8-de7adb46dc41"
DATA_UUID = "6f94d0ef-c13a-4348-bf41-977dd4f15bff"
CREATE_UUID = "5d753dcf-3c18-4810-8ca7-aae75502f5c3"
APP_UUID = "72b6ebe0-3fab-4f64-ae9e-1027848cee96"

CURRENT_ENGINE_MARKER = "function useRenderEngine(onComplete)"

NEW_ENGINE = """function useRenderEngine(onComplete) {
  const [job, setJob] = useState(null);
  const streamRef = useRef(null);
  const stopStream = () => { if (streamRef.current) { streamRef.current.close(); streamRef.current = null; } };

  const buildPayload = (cfg) => ({
    kind: cfg.kind || "prompt",
    prompt: cfg.prompt || "",
    theme: cfg.theme,
    caption: cfg.caption,
    duration: cfg.duration || cfg.targetDur,
    targetDur: cfg.targetDur,
    resolution: cfg.res,
    transition: cfg.transition,
    being: cfg.being,
    emotion: cfg.emotion,
    engine: cfg.engine,
    method: cfg.method,
    clip: cfg.clip,
    input_file_id: cfg.input_file_id,
    input_file_ids: cfg.input_file_ids,
    voice: { being: cfg.being, emotion: cfg.emotion, engine: cfg.engine },
  });

  const run = useCallback(async (cfg, _lineScript) => {
    stopStream();
    setJob({ status: "rendering", progress: 0, lines: [], cfg });
    const api = (window.CVE && window.CVE.API_BASE) || "";
    try {
      const res = await fetch(api + "/api/render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildPayload(cfg)),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || data.error || ("API " + res.status));
      const jobId = data.jobId || data.job_id;
      const es = new EventSource(api + "/api/render/" + jobId + "/stream");
      streamRef.current = es;
      es.addEventListener("log", (e) => {
        const ln = JSON.parse(e.data);
        setJob((j) => j ? { ...j, lines: [...j.lines, { k: ln.k, s: ln.s }] } : j);
      });
      es.addEventListener("progress", (e) => {
        const p = JSON.parse(e.data);
        setJob((j) => j ? { ...j, progress: p.progress || 0 } : j);
      });
      es.addEventListener("done", (e) => {
        const d = JSON.parse(e.data);
        const out = d.outputUrl || null;
        setJob((j) => j ? { ...j, status: "done", progress: 100, outputUrl: out } : j);
        stopStream();
        onComplete && onComplete({ ...cfg, outputUrl: out });
      });
      es.addEventListener("fail", (e) => {
        const d = JSON.parse(e.data);
        const msg = d.s || "render failed";
        setJob((j) => j ? { ...j, status: "error", error: msg, lines: [...j.lines, { k: "err", s: msg }] } : j);
        stopStream();
      });
      es.onerror = () => {
        setJob((j) => j && j.status === "rendering" ? { ...j, status: "error", error: "stream disconnected" } : j);
        stopStream();
      };
    } catch (err) {
      setJob({ status: "error", progress: 0, lines: [{ k: "err", s: String(err.message || err) }], cfg, error: String(err.message || err) });
    }
  }, [onComplete]);

  const reset = useCallback(() => { stopStream(); setJob(null); }, []);
  useEffect(() => () => stopStream(), []);
  return { job, run, reset };
}"""

CURRENT_DROPZONE = """function DropZone({ label, sub, accent = "var(--signal-teal)", onPick }) {
  const [over, setOver] = useState(false);
  return (
    <div onClick={onPick} onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)} onDrop={(e) => { e.preventDefault(); setOver(false); onPick && onPick(); }}
      style={{ cursor: "pointer", border: `1.5px dashed ${over ? accent : "var(--border-soft)"}`,
        borderRadius: 12, padding: "26px 18px", textAlign: "center",
        background: over ? `${accent}11` : "var(--bg-void)", transition: "all .15s var(--ease-soft)" }}>
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 10, color: over ? accent : "var(--fg-3)" }}>
        <Icon name="folder" size={26} />
      </div>
      <div style={{ fontFamily: mono, fontSize: 12.5, color: "var(--fg-1)" }}>{label}</div>
      {sub && <div style={{ fontFamily: mono, fontSize: 10.5, color: "var(--fg-4)", marginTop: 5 }}>{sub}</div>}
    </div>
  );
}"""

NEW_DROPZONE = """function DropZone({ label, sub, accent = "var(--signal-teal)", onPick, onUploaded, multiple = false, accept = "video/*" }) {
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const uploadFiles = async (fileList) => {
    if (!fileList || !fileList.length || !window.CVE.uploadFile) return;
    setBusy(true);
    try {
      const uploaded = [];
      for (const file of fileList) uploaded.push(await window.CVE.uploadFile(file));
      onUploaded && onUploaded(uploaded);
      onPick && onPick(uploaded);
    } catch (err) {
      console.error("[CVE] upload failed", err);
    } finally { setBusy(false); }
  };
  return (
    <div onClick={() => inputRef.current && inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); uploadFiles(e.dataTransfer.files); }}
      style={{ cursor: busy ? "wait" : "pointer", border: `1.5px dashed ${over ? accent : "var(--border-soft)"}`,
        borderRadius: 12, padding: "26px 18px", textAlign: "center",
        background: over ? `${accent}11` : "var(--bg-void)", transition: "all .15s var(--ease-soft)", opacity: busy ? 0.7 : 1 }}>
      <input ref={inputRef} type="file" accept={accept} multiple={multiple} style={{ display: "none" }}
        onChange={(e) => uploadFiles(e.target.files)} />
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 10, color: over ? accent : "var(--fg-3)" }}>
        <Icon name="folder" size={26} />
      </div>
      <div style={{ fontFamily: mono, fontSize: 12.5, color: "var(--fg-1)" }}>{busy ? "Uploading…" : label}</div>
      {sub && <div style={{ fontFamily: mono, fontSize: 10.5, color: "var(--fg-4)", marginTop: 5 }}>{sub}</div>}
    </div>
  );
}"""

AUTOEDIT_SURFACE_OLD = """function AutoEditSurface({ cfg, set, accent, addJob }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Auto-Edit", label: "input.mp4", theme: c.theme, dur: c.duration, stamp: c.stamp }));
  const [loaded, setLoaded] = useStateC(false);
  const rendering = engine.job && engine.job.status === "rendering";
  const start = () => {
    const stamp = Date.now().toString().slice(-6);
    const c = { ...cfg, kind: "autoedit", clip: cfg.clip, duration: cfg.targetDur, stamp };
    engine.run(c, window.CVE.logs.autoedit(c));
  };
  return (
    <SurfaceShell id="autoedit"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {loaded ? (
            <Panel pad={14} style={{ background: "var(--bg-void)", display: "flex", alignItems: "center", gap: 12 }}>
              <Placeholder label="src" style={{ width: 76, height: 44, borderRadius: 6, flexShrink: 0 }} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--fg-1)" }}>input.mp4</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fg-4)" }}>14m22s · 25fps · 1.2 GB</div>
              </div>
              <button onClick={() => setLoaded(false)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--fg-4)", fontFamily: "var(--font-mono)", fontSize: 11 }}>✕</button>
            </Panel>
          ) : (
            <DropZone label="Drop a long take — input.mp4" sub="MP4 · MOV · up to 4 GB" accent={accent} onPick={() => setLoaded(true)} />
          )}
"""

AUTOEDIT_SURFACE_NEW = """function AutoEditSurface({ cfg, set, accent, addJob }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Auto-Edit", label: c.uploadName || "source", theme: c.theme, dur: c.duration, stamp: c.stamp, outputUrl: c.outputUrl }));
  const [upload, setUpload] = useStateC(null);
  const rendering = engine.job && engine.job.status === "rendering";
  const start = () => {
    if (!upload) return;
    const stamp = Date.now().toString().slice(-6);
    const c = { ...cfg, kind: "autoedit", clip: cfg.clip, duration: cfg.targetDur, stamp, input_file_id: upload.fileId, uploadName: upload.name };
    engine.run(c, window.CVE.logs.autoedit(c));
  };
  return (
    <SurfaceShell id="autoedit"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {upload ? (
            <Panel pad={14} style={{ background: "var(--bg-void)", display: "flex", alignItems: "center", gap: 12 }}>
              <Placeholder label="src" style={{ width: 76, height: 44, borderRadius: 6, flexShrink: 0 }} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--fg-1)" }}>{upload.name}</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fg-4)" }}>{(upload.size / (1024*1024)).toFixed(1)} MB · ready</div>
              </div>
              <button onClick={() => setUpload(null)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--fg-4)", fontFamily: "var(--font-mono)", fontSize: 11 }}>✕</button>
            </Panel>
          ) : (
            <DropZone label="Drop a long take — input.mp4" sub="MP4 · MOV · up to 4 GB" accent={accent} onUploaded={(files) => setUpload(files[0])} />
          )}
"""

HIGHLIGHTS_SURFACE_OLD = """function HighlightsSurface({ cfg, set, accent, addJob }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Highlights", label: `method:${c.method}`, theme: c.theme, dur: 0, stamp: c.stamp }));
  const [loaded, setLoaded] = useStateC(true);
  const rendering = engine.job && engine.job.status === "rendering";
  const moments = [
    { t: "00:42", score: 0.94, label: "key statement" },
    { t: "03:18", score: 0.88, label: "audience laugh" },
    { t: "07:55", score: 0.81, label: "demo reveal" },
    { t: "11:09", score: 0.76, label: "closing line" },
  ];
  const start = () => {
    const stamp = Date.now().toString().slice(-6);
    engine.run({ ...cfg, kind: "highlights", stamp }, window.CVE.logs.highlights({ ...cfg, stamp }));
  };
  return (
    <SurfaceShell id="highlights"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {loaded ? (
            <Panel pad={14} style={{ background: "var(--bg-void)", display: "flex", alignItems: "center", gap: 12 }}>
              <Placeholder label="src" style={{ width: 76, height: 44, borderRadius: 6, flexShrink: 0 }} />
              <div><div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--fg-1)" }}>input.mp4</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fg-4)" }}>14m22s source</div></div>
            </Panel>
          ) : <DropZone label="Drop source — input.mp4" accent={accent} onPick={() => setLoaded(true)} />}
          <Field label="Detection method">
            <Seg options={[{id:"scene",label:"scene"},{id:"audio",label:"audio"},{id:"transcript",label:"transcript"}]}
              value={cfg.method} onChange={(v) => set("method", v)} accent={accent} />
          </Field>
          <Field label="Detected moments" hint="auto-ranked">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {moments.map((m, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, background: "var(--bg-void)",
                  border: "1px solid var(--border-hairline)", borderRadius: 9, padding: "10px 12px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: accent }}>{m.t}</span>
                  <span style={{ fontFamily: "var(--font-sans)", fontSize: 13, color: "var(--fg-2)", flex: 1 }}>{m.label}</span>
                  <div style={{ width: 60 }}><Progress value={m.score * 100} accent={accent} /></div>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fg-3)" }}>{m.score.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </Field>
          <Btn onClick={start} accent={accent} icon="spark2" full disabled={rendering}>{rendering ? "Extracting…" : "Extract highlights"}</Btn>
"""

HIGHLIGHTS_SURFACE_NEW = """function HighlightsSurface({ cfg, set, accent, addJob }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Highlights", label: `method:${c.method}`, theme: c.theme, dur: 0, stamp: c.stamp, outputUrl: c.outputUrl }));
  const [upload, setUpload] = useStateC(null);
  const rendering = engine.job && engine.job.status === "rendering";
  const start = () => {
    if (!upload) return;
    const stamp = Date.now().toString().slice(-6);
    engine.run({ ...cfg, kind: "highlights", stamp, input_file_id: upload.fileId }, window.CVE.logs.highlights({ ...cfg, stamp }));
  };
  return (
    <SurfaceShell id="highlights"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {upload ? (
            <Panel pad={14} style={{ background: "var(--bg-void)", display: "flex", alignItems: "center", gap: 12 }}>
              <Placeholder label="src" style={{ width: 76, height: 44, borderRadius: 6, flexShrink: 0 }} />
              <div><div style={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "var(--fg-1)" }}>{upload.name}</div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--fg-4)" }}>{(upload.size / (1024*1024)).toFixed(1)} MB · ready</div></div>
            </Panel>
          ) : <DropZone label="Drop source — input.mp4" accent={accent} onUploaded={(files) => setUpload(files[0])} />}
          <Field label="Detection method">
            <Seg options={[{id:"scene",label:"scene"},{id:"audio",label:"audio"},{id:"transcript",label:"transcript"}]}
              value={cfg.method} onChange={(v) => set("method", v)} accent={accent} />
          </Field>
          <Field label="Pipeline log" hint="real highlights land in the log + preview">
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-3)", lineHeight: 1.5 }}>
              Upload a source file, pick a method, then extract. Moments appear in the pipeline log as the engine runs.
            </div>
          </Field>
          <Btn onClick={start} accent={accent} icon="spark2" full disabled={rendering || !upload}>{rendering ? "Extracting…" : "Extract highlights"}</Btn>
"""

MONTAGE_SURFACE_OLD = """function MontageSurface({ cfg, set, accent, addJob }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Montage", label: `${c.clipCount} clips`, theme: c.theme, dur: c.duration, stamp: c.stamp }));
  const [clips, setClips] = useStateC(["vid1.mp4", "vid2.mp4", "vid3.mp4"]);
  const rendering = engine.job && engine.job.status === "rendering";
  const start = () => {
    const stamp = Date.now().toString().slice(-6);
    const c = { ...cfg, kind: "montage", duration: cfg.targetDur, clipCount: clips.length, clipsLabel: clips.join(" "), stamp };
    engine.run(c, window.CVE.logs.montage(c));
  };
  return (
    <SurfaceShell id="montage"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Clips" hint={`${clips.length} queued`}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {clips.map((c, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--bg-void)",
                  border: "1px solid var(--border-hairline)", borderRadius: 9, padding: "8px 10px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-4)", width: 18 }}>{i+1}</span>
                  <Placeholder label="" style={{ width: 44, height: 26, borderRadius: 4 }} />
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fg-2)", flex: 1 }}>{c}</span>
                  <button onClick={() => setClips(clips.filter((_, j) => j !== i))} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--fg-4)", fontFamily: "var(--font-mono)" }}>✕</button>
                </div>
              ))}
              <button onClick={() => setClips([...clips, `vid${clips.length+1}.mp4`])} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                cursor: "pointer", background: "transparent", border: "1.5px dashed var(--border-soft)", borderRadius: 9, padding: "9px",
                color: "var(--fg-3)", fontFamily: "var(--font-mono)", fontSize: 11.5 }}>
                <Icon name="plus" size={14} /> add clip
              </button>
            </div>
          </Field>
"""

MONTAGE_SURFACE_NEW = """function MontageSurface({ cfg, set, accent, addJob }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Montage", label: `${c.clipCount} clips`, theme: c.theme, dur: c.duration, stamp: c.stamp, outputUrl: c.outputUrl }));
  const [clips, setClips] = useStateC([]);
  const rendering = engine.job && engine.job.status === "rendering";
  const start = () => {
    const stamp = Date.now().toString().slice(-6);
    const c = { ...cfg, kind: "montage", duration: cfg.targetDur, clipCount: clips.length, clipsLabel: clips.map((x) => x.name).join(" "), stamp, input_file_ids: clips.map((x) => x.fileId) };
    engine.run(c, window.CVE.logs.montage(c));
  };
  const addClips = (files) => setClips((prev) => [...prev, ...files]);
  return (
    <SurfaceShell id="montage"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Clips" hint={`${clips.length} uploaded`}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {clips.map((c, i) => (
                <div key={c.fileId || i} style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--bg-void)",
                  border: "1px solid var(--border-hairline)", borderRadius: 9, padding: "8px 10px" }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-4)", width: 18 }}>{i+1}</span>
                  <Placeholder label="" style={{ width: 44, height: 26, borderRadius: 4 }} />
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--fg-2)", flex: 1 }}>{c.name}</span>
                  <button onClick={() => setClips(clips.filter((_, j) => j !== i))} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--fg-4)", fontFamily: "var(--font-mono)" }}>✕</button>
                </div>
              ))}
              <DropZone label="Add clips" sub="MP4 · MOV · select multiple" accent={accent} multiple onUploaded={addClips} />
            </div>
          </Field>
"""

PROMPT_ADDJOB_OLD = 'const engine = useRenderEngine((c) => addJob({ kind: "Prompt", label: c.promptShort, theme: c.theme, dur: c.duration, stamp: c.stamp }));'
PROMPT_ADDJOB_NEW = 'const engine = useRenderEngine((c) => addJob({ kind: "Prompt", label: c.promptShort, theme: c.theme, dur: c.duration, stamp: c.stamp, outputUrl: c.outputUrl }));'

PROMPT_SURFACE_OLD = """function PromptSurface({ cfg, set, accent, addJob, goVoice }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Prompt", label: c.promptShort, theme: c.theme, dur: c.duration, stamp: c.stamp, outputUrl: c.outputUrl }));
  const being = window.CVE.BEINGS.find((b) => b.id === cfg.being) || window.CVE.BEINGS[0];
  const rendering = engine.job && engine.job.status === "rendering";

  const start = () => {
    const promptShort = (cfg.prompt || "").slice(0, 46).replace(/\\s+$/, "") + (cfg.prompt.length > 46 ? "…" : "");
    const stamp = Date.now().toString().slice(-6);
    const c = { ...cfg, kind: "prompt", promptShort, stamp, being: cfg.being };
    engine.run(c, window.CVE.logs.prompt(c));
  };

  return (
    <SurfaceShell id="prompt"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Prompt" hint={`${cfg.prompt.length} chars`}>
            <textarea value={cfg.prompt} onChange={(e) => set("prompt", e.target.value)} rows={4} style={{
              width: "100%", resize: "vertical", boxSizing: "border-box",
              background: "var(--bg-void)", color: "var(--fg-1)", ...COPPER,
              borderRadius: 10, padding: "12px 14px", fontFamily: "var(--font-sans)", fontSize: 14, lineHeight: 1.5 }} />
          </Field>"""

PROMPT_SURFACE_NEW = """function PromptSurface({ cfg, set, accent, addJob, goVoice }) {
  const engine = useRenderEngine((c) => addJob({ kind: "Prompt", label: c.promptShort, theme: c.theme, dur: c.duration, stamp: c.stamp, outputUrl: c.outputUrl }));
  const being = window.CVE.BEINGS.find((b) => b.id === cfg.being) || window.CVE.BEINGS[0];
  const rendering = engine.job && engine.job.status === "rendering";
  const [doc, setDoc] = useState(null);
  const [docBusy, setDocBusy] = useState(false);

  const [docErr, setDocErr] = useState(null);

  const ingestDocument = async (files) => {
    const f = files && files[0];
    if (!f) return;
    setDoc(f);
    setDocBusy(true);
    setDocErr(null);
    const api = (window.CVE && window.CVE.API_BASE) || "";
    try {
      const r = await fetch(api + "/api/documents/" + f.fileId + "/extract");
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.detail || j.error || ("extract " + r.status));
      if (j.text) set("prompt", j.text);
      else throw new Error("No text extracted from document");
    } catch (err) {
      const msg = String(err.message || err);
      setDocErr(msg);
      console.error("[CVE] document extract failed", err);
    } finally {
      setDocBusy(false);
    }
  };

  const start = () => {
    if (!cfg.prompt.trim() && !doc) return;
    const base = cfg.prompt.trim() || (doc ? doc.name : "");
    const promptShort = base.slice(0, 46).replace(/\\s+$/, "") + (base.length > 46 ? "…" : "");
    const stamp = Date.now().toString().slice(-6);
    const c = { ...cfg, kind: "prompt", promptShort, stamp, being: cfg.being, input_file_id: doc ? doc.fileId : undefined };
    engine.run(c, window.CVE.logs.prompt(c));
  };

  return (
    <SurfaceShell id="prompt"
      left={
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Field label="Prompt" hint={`${cfg.prompt.length} chars · optional if document attached`}>
            <textarea value={cfg.prompt} onChange={(e) => set("prompt", e.target.value)} rows={4} style={{
              width: "100%", resize: "vertical", boxSizing: "border-box",
              background: "var(--bg-void)", color: "var(--fg-1)", ...COPPER,
              borderRadius: 10, padding: "12px 14px", fontFamily: "var(--font-sans)", fontSize: 14, lineHeight: 1.5 }} />
          </Field>
          <Field label="Source document" hint="PDF · HTML · TXT · images — text loads into prompt for editing">
            <DropZone label={docBusy ? "Extracting text…" : (doc ? doc.name : "Drop document")}
              sub={docErr ? docErr : (doc ? `${(doc.size / 1024).toFixed(0)} KB · edit prompt above before render` : "email export, brief, scanned page")}
              accent={docErr ? "var(--signal-red)" : accent}
              accept=".pdf,.html,.htm,.txt,.md,.png,.jpg,.jpeg,application/pdf,text/html,text/plain,image/*"
              onUploaded={ingestDocument} />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px 16px" }}>
            <Field label="Theme"><Select options={window.CVE.THEMES} value={cfg.theme} onChange={(v) => set("theme", v)} /></Field>
            <Field label="Caption"><Select options={window.CVE.CAPTION_STYLES} value={cfg.caption} onChange={(v) => set("caption", v)} /></Field>
            <Field label="Duration" hint={`${cfg.duration}s`}>
              <input type="range" min={15} max={120} step={5} value={cfg.duration}
                onChange={(e) => set("duration", +e.target.value)} className="cve-range" style={{ width: "100%", accentColor: accent }} />
            </Field>
            <Field label="Resolution"><Seg options={window.CVE.RESOLUTIONS} value={cfg.res} onChange={(v) => set("res", v)} accent={accent} /></Field>
          </div>
          <Field label="Transition"><Seg options={window.CVE.TRANSITIONS} value={cfg.transition} onChange={(v) => set("transition", v)} accent="#5BE881" /></Field>
          <VoicePanelCompact cfg={cfg} set={set} goVoice={goVoice} />
          <div style={{ display: "flex", gap: 10 }}>
            <Btn onClick={start} accent={accent} icon="spark" full disabled={rendering || (!cfg.prompt.trim() && !doc)}>
              {rendering ? "Rendering…" : "Render video"}
            </Btn>
            {engine.job && <Btn kind="ghost" onClick={engine.reset}>Reset</Btn>}
          </div>
        </div>
      }
      right={<RenderView engine={engine} cfg={cfg} accent={accent} beingColor={being.color}
        captionText={"Today we'll learn three new things."} label="prompt → video" />}
    />
  );
}"""

AUTOEDIT_BTN_OLD = 'disabled={rendering || !loaded}'
AUTOEDIT_BTN_NEW = 'disabled={rendering || !upload}'

RECENT_STRIP_OLD = """          <span style={{ color: "var(--fg-4)", display: "flex" }}><Icon name="dl" size={13} /></span>"""
RECENT_STRIP_NEW = """          {j.outputUrl ? (
            <a href={j.outputUrl} download style={{ color: "var(--signal-teal)", display: "flex" }} title="Download render"><Icon name="dl" size={13} /></a>
          ) : (
            <span style={{ color: "var(--fg-4)", display: "flex", opacity: 0.35 }}><Icon name="dl" size={13} /></span>
          )}"""

ERROR_STATUS_PATCHES = [
    ('status === "failed"', 'status === "error"'),
    ('status === "failed" ? "FAILED"', 'status === "error" ? "FAILED"'),
    ('status === "failed" ? "var(--signal-red)"', 'status === "error" ? "var(--signal-red)"'),
]

UPLOAD_FN = """
async function uploadFile(file) {
  const api = API_BASE || "";
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(api + "/api/upload", { method: "POST", body });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || ("upload " + res.status));
  return data;
}
"""

API_INJECT = """
const API_BASE = (typeof window !== "undefined" && window.location && window.location.protocol.startsWith("http"))
  ? "" : "http://127.0.0.1:8618";
"""


def decode_entry(entry: dict) -> str:
    data = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        data = gzip.decompress(data)
    return data.decode("utf-8")


def encode_entry(src: str, mime: str = "text/javascript") -> dict:
    raw = src.encode("utf-8")
    compressed = gzip.compress(raw)
    use = compressed if len(compressed) < len(raw) else raw
    return {
        "mime": mime,
        "compressed": use is compressed,
        "data": base64.b64encode(use).decode("ascii"),
    }


def replace_engine(ui: str) -> str:
    start = ui.find(CURRENT_ENGINE_MARKER)
    if start < 0:
        raise SystemExit("useRenderEngine not found")
    end = ui.find("// ───────────────────────── Preview Stage", start)
    if end < 0:
        raise SystemExit("PreviewStage marker not found")
    return ui[:start] + NEW_ENGINE + "\n\n" + ui[end:]


def patch() -> None:
    text = CLIENT.read_text(encoding="utf-8")
    manifest = json.loads(re.search(r'<script type="__bundler/manifest">\n(.+?)\n  </script>', text, re.DOTALL).group(1))

    ui = decode_entry(manifest[UI_UUID])
    ui = replace_engine(ui)
    if "uploadFiles" not in ui and CURRENT_DROPZONE in ui:
        ui = ui.replace(CURRENT_DROPZONE, NEW_DROPZONE)
    elif "uploadFiles" not in ui:
        raise SystemExit("DropZone block not found and upload wiring missing")
    for old, new in ERROR_STATUS_PATCHES:
        ui = ui.replace(old, new)
    manifest[UI_UUID] = encode_entry(ui)

    data = decode_entry(manifest[DATA_UUID])
    data = re.sub(
        r'const API_BASE = \(typeof window[\s\S]*?\? "" : "http://127\.0\.0\.1:8618";\n\n',
        "",
        data,
    )
    data = re.sub(
        r"async function uploadFile\(file\) \{[\s\S]*?\n\}\n\n",
        "",
        data,
    )
    data = data.replace(
        "window.CVE = {\n  API_BASE,\n  uploadFile,\n  API_BASE,",
        "window.CVE = {\n  API_BASE,\n  uploadFile,",
    )
    marker = "// All values attached to window.CVE for cross-file (Babel) access."
    inject = API_INJECT.strip() + "\n\n" + UPLOAD_FN.strip() + "\n"
    if marker in data:
        if data.count("const API_BASE") == 0:
            data = data.replace(marker, marker + "\n" + inject)
    elif "uploadFile" not in data:
        data = data.replace(
            "window.CVE = {",
            inject + "window.CVE = {\n  API_BASE,\n  uploadFile,",
        )
    if data.count("const API_BASE") != 1:
        raise SystemExit(f"Expected one API_BASE declaration, found {data.count('const API_BASE')}")
    manifest[DATA_UUID] = encode_entry(data)

    create = decode_entry(manifest[CREATE_UUID])
    replacements = [
        (PROMPT_ADDJOB_OLD, PROMPT_ADDJOB_NEW),
        (AUTOEDIT_SURFACE_OLD, AUTOEDIT_SURFACE_NEW),
        (AUTOEDIT_BTN_OLD, AUTOEDIT_BTN_NEW),
        (HIGHLIGHTS_SURFACE_OLD, HIGHLIGHTS_SURFACE_NEW),
        (MONTAGE_SURFACE_OLD, MONTAGE_SURFACE_NEW),
    ]
    for old, new in replacements:
        if old in create:
            create = create.replace(old, new)
        elif new.split("(", 1)[0] not in create:
            raise SystemExit(f"Missing create patch block: {old[:80]}")
    if PROMPT_SURFACE_OLD in create:
        create = create.replace(PROMPT_SURFACE_OLD, PROMPT_SURFACE_NEW)
    elif "function PromptSurface" in create:
        start = create.find("function PromptSurface")
        end = create.find("// ───────────────────────── AUTO-EDIT", start)
        if end < 0:
            end = create.find("function AutoEditSurface", start)
        if start < 0 or end < 0:
            raise SystemExit("PromptSurface block boundaries not found")
        create = create[:start] + PROMPT_SURFACE_NEW + "\n\n" + create[end:]
    elif "Source document" not in create:
        raise SystemExit("PromptSurface document dropzone block not found")
    manifest[CREATE_UUID] = encode_entry(create)

    app = decode_entry(manifest[APP_UUID])
    if RECENT_STRIP_OLD in app:
        app = app.replace(RECENT_STRIP_OLD, RECENT_STRIP_NEW)
        manifest[APP_UUID] = encode_entry(app)

    new_manifest = json.dumps(manifest, separators=(",", ":"))
    text = re.sub(
        r'<script type="__bundler/manifest">\n.*?\n  </script>',
        f'<script type="__bundler/manifest">\n{new_manifest}\n  </script>',
        text,
        count=1,
        flags=re.DOTALL,
    )
    CLIENT.write_text(text, encoding="utf-8")
    print(f"Patched {CLIENT}")


if __name__ == "__main__":
    patch()