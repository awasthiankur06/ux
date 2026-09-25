import { useRef } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Upload, Zap, Palette } from "lucide-react";

export function InputPanel({
  srsText, setSrsText, url, setUrl, crawlDepth, setCrawlDepth, onSubmit, loading, onFileSelect,
  brandFileName, onBrandFileSelect, designSystem, setDesignSystem,
}) {
  const fileRef = useRef(null);
  const brandFileRef = useRef(null);

  return (
    <div className="p-4 border-b border-border space-y-4" data-testid="input-panel">
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">01 // SRS Input</p>
        <Textarea
          data-testid="srs-textarea"
          value={srsText}
          onChange={(e) => setSrsText(e.target.value)}
          placeholder="Paste SRS / product requirement text here..."
          className="rounded-none bg-transparent border-border font-mono text-xs min-h-[100px] focus-visible:ring-1 focus-visible:ring-primary"
        />
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.pdf"
          data-testid="srs-file-input"
          className="hidden"
          onChange={(e) => e.target.files[0] && onFileSelect(e.target.files[0])}
        />
        <button
          data-testid="srs-upload-button"
          onClick={() => fileRef.current?.click()}
          className="mt-2 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-secondary hover:text-white transition-colors"
        >
          <Upload className="w-3 h-3" /> Upload .txt / .pdf
        </button>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">02 // Website URL</p>
        <Input
          data-testid="url-input"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://existing-app.com"
          className="rounded-none bg-transparent border-border font-mono text-xs focus-visible:ring-1 focus-visible:ring-primary"
        />
        <div className="flex mt-2 border border-border">
          {["single", "multi"].map((mode) => (
            <button
              key={mode}
              data-testid={`crawl-depth-${mode}`}
              onClick={() => setCrawlDepth(mode)}
              className={`flex-1 text-[10px] uppercase tracking-wide py-1.5 transition-colors ${
                crawlDepth === mode ? "bg-primary text-black" : "text-muted-foreground hover:text-white"
              }`}
            >
              {mode === "single" ? "Single Page" : "Multi Page"}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">03 // Design System</p>
        <div className="border border-border" data-testid="design-system-selector">
          <label className={`flex gap-2 p-2.5 cursor-pointer transition-colors ${designSystem === "standard" ? "bg-primary/10" : "hover:bg-muted/30"}`}>
            <input
              type="radio"
              name="design-system"
              value="standard"
              checked={designSystem === "standard"}
              onChange={() => setDesignSystem("standard")}
              data-testid="design-system-standard"
              className="mt-0.5 accent-primary"
            />
            <span>
              <span className="block text-[11px] font-medium">Standard UX</span>
              <span className="block text-[10px] text-muted-foreground mt-0.5">Uses the current wireframe generation flow.</span>
            </span>
          </label>
          <label className={`flex gap-2 p-2.5 border-t border-border cursor-pointer transition-colors ${designSystem === "dbim_gov" ? "bg-primary/10" : "hover:bg-muted/30"}`}>
            <input
              type="radio"
              name="design-system"
              value="dbim_gov"
              checked={designSystem === "dbim_gov"}
              onChange={() => setDesignSystem("dbim_gov")}
              data-testid="design-system-gov-compliance"
              className="mt-0.5 accent-primary"
            />
            <span>
              <span className="block text-[11px] font-medium">Gov Compliance — Design Pre-check</span>
              <span className="block text-[10px] text-muted-foreground mt-0.5">DBIM and GIGW 3.0 checks will be applied before export.</span>
            </span>
          </label>
        </div>
      </div>

      <Button
        data-testid="initialize-orchestrator-button"
        onClick={onSubmit}
        disabled={loading || (!srsText && !url)}
        className="w-full rounded-none bg-primary text-black hover:bg-white font-chivo font-bold uppercase tracking-wide text-xs gap-2 disabled:opacity-40"
      >
        <Zap className="w-3.5 h-3.5" />
        {loading ? "Orchestrating..." : "Initialize Orchestrator"}
      </Button>

      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-2">04 // Brand Kit (Optional)</p>
        <input
          ref={brandFileRef}
          type="file"
          accept=".html,.css,.txt,.json"
          data-testid="brand-file-input"
          className="hidden"
          onChange={(e) => e.target.files[0] && onBrandFileSelect(e.target.files[0])}
        />
        <button
          data-testid="brand-upload-button"
          onClick={() => brandFileRef.current?.click()}
          className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-secondary hover:text-white transition-colors"
        >
          <Palette className="w-3 h-3" /> {brandFileName || "Upload CSS/HTML brand reference"}
        </button>
      </div>
    </div>
  );
}
