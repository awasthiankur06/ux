import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, RotateCw, Lock, MousePointerClick, ExternalLink } from "lucide-react";
import { allWireframesPreviewUrl } from "@/lib/api";

const COMMENT_SCRIPT = `
<script>
(function(){
  var commentMode = false;
  window.addEventListener('message', function(e){
    if (e.data && e.data.type === 'toggle-comment-mode') commentMode = e.data.value;
  });
  document.addEventListener('mouseover', function(e){
    if (!commentMode) return;
    e.target.style.outline = '2px solid #00E5FF';
    e.target.style.cursor = 'crosshair';
  }, true);
  document.addEventListener('mouseout', function(e){
    if (!commentMode) return;
    e.target.style.outline = '';
  }, true);
  document.addEventListener('click', function(e){
    if (!commentMode) return;
    e.preventDefault(); e.stopPropagation();
    var el = e.target;
    var descriptor = '<' + el.tagName.toLowerCase() +
      (el.className ? ' class="' + String(el.className).slice(0,120) + '"' : '') +
      '> text: "' + (el.textContent || '').trim().slice(0, 80) + '"';
    window.parent.postMessage({ source: 'ux-orchestrator-wireframe', type: 'element-selected', descriptor: descriptor }, '*');
  }, true);
})();
</script>`;

const DBIM_STYLESHEET = "/design-systems/dbim/Compiled/css/compiled.min.css";
const DBIM_SCRIPT = "/design-systems/dbim/Compiled/js/compiled.bundle.min.js";

function injectCommentScript(html, designSystem) {
  if (!html) return html;
  // srcDoc has an about:srcdoc base URL. Make local DBIM package references point
  // to the frontend that is currently serving Studio, not to the API/preview page.
  const frontendBase = window.location.origin;
  let prepared = html.replace(/(["'])\/design-systems\//g, `$1${frontendBase}/design-systems/`);
  const baseTag = `<base href="${frontendBase}/">`;
  const dbimAssets = designSystem === "dbim_gov"
    ? `${prepared.includes(DBIM_STYLESHEET) ? "" : `<link rel="stylesheet" href="${frontendBase}${DBIM_STYLESHEET}">`}${prepared.includes(DBIM_SCRIPT) ? "" : `<script src="${frontendBase}${DBIM_SCRIPT}"></script>`}`
    : "";
  if (prepared.includes("</head>")) prepared = prepared.replace("</head>", baseTag + dbimAssets + "</head>");
  else prepared = `<head>${baseTag}${dbimAssets}</head>` + prepared;
  if (prepared.includes("</body>")) return prepared.replace("</body>", COMMENT_SCRIPT + "</body>");
  return prepared + COMMENT_SCRIPT;
}

export function WirePreview({ wireframes, activeIdx, setActiveIdx, commentMode, setCommentMode, onElementSelected, runId, designSystem }) {
  const iframeRef = useRef(null);
  const idx = Math.min(activeIdx, Math.max(0, (wireframes?.length || 1) - 1));

  useEffect(() => {
    const handler = (e) => {
      if (e.data?.source === "ux-orchestrator-wireframe" && e.data?.type === "element-selected") {
        onElementSelected?.(e.data.descriptor);
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [onElementSelected]);

  const sendCommentMode = useCallback(() => {
    iframeRef.current?.contentWindow?.postMessage({ type: "toggle-comment-mode", value: commentMode }, "*");
  }, [commentMode]);

  useEffect(() => { sendCommentMode(); }, [sendCommentMode]);

  if (!wireframes || wireframes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-xs" data-testid="wireframe-empty">
        Live wireframe previews will render here once the Wireframe Generator completes.
      </div>
    );
  }

  const current = wireframes[idx];

  const openAllInNewTab = () => {
    if (!runId) return;
    window.open(allWireframesPreviewUrl(runId), "_blank", "noopener,noreferrer");
  };

  return (
    <div className="h-full flex flex-col" data-testid="wire-preview">
      <div className="flex overflow-x-auto border-b border-border">
        {wireframes.map((w, i) => (
          <button
            key={i}
            data-testid={`wireframe-tab-${i}`}
            onClick={() => setActiveIdx(i)}
            className={`px-3 py-2 text-[11px] uppercase tracking-wide whitespace-nowrap border-r border-border transition-colors ${
              i === idx ? "bg-primary text-black" : "text-muted-foreground hover:text-white"
            }`}
          >
            {w.screen_name}
          </button>
        ))}
      </div>
      <div className="flex-1 p-4 flex flex-col min-h-0">
        <div className="flex items-center gap-3 border border-border border-b-0 bg-surface px-3 py-2 shrink-0">
          <div className="flex gap-1.5 shrink-0">
            <span className="w-2.5 h-2.5 rounded-full bg-destructive/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-primary/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#34C759]/70" />
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground shrink-0">
            <ChevronLeft className="w-3.5 h-3.5" />
            <ChevronRight className="w-3.5 h-3.5" />
            <RotateCw className="w-3 h-3" />
          </div>
          <div className="flex-1 flex items-center gap-1.5 bg-background border border-border rounded-full px-3 py-1 min-w-0">
            <Lock className="w-2.5 h-2.5 text-muted-foreground shrink-0" />
            <span className="text-[10px] text-muted-foreground truncate">
              app.local/{current.screen_name.toLowerCase().replace(/\s+/g, "-")}
            </span>
          </div>
          <button
            data-testid="comment-mode-toggle"
            onClick={() => setCommentMode(!commentMode)}
            className={`flex items-center gap-1 text-[10px] uppercase tracking-wide px-2 py-1 border shrink-0 transition-colors ${
              commentMode ? "bg-secondary text-black border-secondary" : "text-muted-foreground border-border hover:text-white"
            }`}
          >
            <MousePointerClick className="w-3 h-3" /> Comment
          </button>
          <button
            data-testid="open-all-wireframes-button"
            onClick={openAllInNewTab}
            disabled={!runId}
            className="flex items-center gap-1 text-[10px] uppercase tracking-wide px-2 py-1 border shrink-0 text-muted-foreground border-border hover:text-white disabled:opacity-40"
            title="Open all generated screens in a responsive preview tab"
          >
            <ExternalLink className="w-3 h-3" /> Open All
          </button>
        </div>
        <iframe
          ref={iframeRef}
          data-testid="wireframe-iframe"
          title={current.screen_name}
          srcDoc={injectCommentScript(current.html, designSystem)}
          onLoad={sendCommentMode}
          className="flex-1 w-full border border-border bg-white min-h-0"
          sandbox="allow-scripts"
        />
        <div className="flex justify-between mt-3 shrink-0">
          <button
            data-testid="wireframe-prev-button"
            onClick={() => setActiveIdx(Math.max(0, idx - 1))}
            disabled={idx === 0}
            className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground hover:text-white disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" /> Prev
          </button>
          <span className="text-[11px] text-muted-foreground">{idx + 1} / {wireframes.length}</span>
          <button
            data-testid="wireframe-next-button"
            onClick={() => setActiveIdx(Math.min(wireframes.length - 1, idx + 1))}
            disabled={idx === wireframes.length - 1}
            className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground hover:text-white disabled:opacity-30 transition-colors"
          >
            Next <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
