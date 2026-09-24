import { useEffect, useState } from "react";
import { finalizeRun, downloadRunUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PackageCheck, Download, Loader2 } from "lucide-react";

export function ExportPanel({ run, runId }) {
  const [activeFile, setActiveFile] = useState(0);
  const [section, setSection] = useState("react");
  const [requested, setRequested] = useState(false);

  const canFinalize = run?.wireframes?.length > 0;
  const exportData = run?.export;
  const exportStatus = run?.export_status;
  const generating = exportStatus === "generating";

  useEffect(() => {
    if (exportStatus === "completed" || exportStatus === "error") setRequested(false);
  }, [exportStatus]);

  const handleFinalize = async () => {
    setRequested(true);
    try {
      await finalizeRun(runId);
    } catch (e) {
      console.error(e);
      setRequested(false);
    }
  };

  if (!exportData) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 p-6 text-center" data-testid="export-panel-empty">
        <p className="text-xs text-muted-foreground">
          Once wireframes are ready, finalize to generate production React + CSS components, an API spec, and a README.
        </p>
        <Button
          data-testid="finalize-export-button"
          onClick={handleFinalize}
          disabled={!canFinalize || generating || requested}
          className="rounded-none bg-secondary text-black hover:bg-white font-chivo font-bold uppercase tracking-wide text-xs gap-2 disabled:opacity-40"
        >
          {generating || requested ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PackageCheck className="w-3.5 h-3.5" />}
          {generating || requested ? "Generating..." : "Finalize & Export"}
        </Button>
        {exportStatus === "error" && (
          <p className="text-[11px] text-destructive" data-testid="export-error-message">
            Export generation failed: {run?.export_error}
          </p>
        )}
      </div>
    );
  }

  const sections = ["react", "css", "api", "readme"];

  return (
    <div className="h-full flex flex-col" data-testid="export-panel-result">
      <div className="flex border-b border-border">
        {sections.map((s) => (
          <button
            key={s}
            data-testid={`export-section-${s}`}
            onClick={() => setSection(s)}
            className={`flex-1 text-[10px] uppercase tracking-wide py-2 transition-colors ${
              section === s ? "bg-primary text-black" : "text-muted-foreground hover:text-white"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {section === "react" && (
          <div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {exportData.react_components?.map((c, i) => (
                <button
                  key={i}
                  data-testid={`export-react-file-${i}`}
                  onClick={() => setActiveFile(i)}
                  className={`text-[10px] px-2 py-1 border border-border ${activeFile === i ? "text-primary border-primary" : "text-muted-foreground"}`}
                >
                  {c.filename}
                </button>
              ))}
            </div>
            <pre className="text-[10px] whitespace-pre-wrap text-muted-foreground bg-surface p-2 border border-border" data-testid="export-code-block">
              {exportData.react_components?.[activeFile]?.code}
            </pre>
          </div>
        )}
        {section === "css" && (
          <pre className="text-[10px] whitespace-pre-wrap text-muted-foreground bg-surface p-2 border border-border">{exportData.css}</pre>
        )}
        {section === "api" && (
          <pre className="text-[10px] whitespace-pre-wrap text-muted-foreground bg-surface p-2 border border-border">
            {JSON.stringify(exportData.api_spec, null, 2)}
          </pre>
        )}
        {section === "readme" && (
          <pre className="text-[10px] whitespace-pre-wrap text-muted-foreground bg-surface p-2 border border-border">{exportData.readme}</pre>
        )}
      </div>

      <a href={downloadRunUrl(runId)} data-testid="download-zip-link" className="m-3">
        <Button className="w-full rounded-none bg-primary text-black hover:bg-white font-chivo font-bold uppercase tracking-wide text-xs gap-2">
          <Download className="w-3.5 h-3.5" /> Download ZIP
        </Button>
      </a>
    </div>
  );
}
