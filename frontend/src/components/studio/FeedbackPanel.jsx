import { useRef, useState } from "react";
import { submitFeedback } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Sparkles, Paperclip, Loader2, CheckCircle2, XCircle, X } from "lucide-react";

const COLOR_PRESETS = [
  { name: "Indigo", hex: "#4F46E5" },
  { name: "Emerald", hex: "#10B981" },
  { name: "Coral", hex: "#F97316" },
  { name: "Rose", hex: "#F43F5E" },
  { name: "Amber", hex: "#F59E0B" },
  { name: "Cyan", hex: "#06B6D4" },
];
const ROUNDNESS_PRESETS = [
  { label: "Sharp", text: "Use sharp corners (no border-radius) for buttons and cards throughout." },
  { label: "Soft", text: "Use soft rounded corners (rounded-xl) for buttons and cards throughout." },
  { label: "Pill", text: "Use fully pill-shaped rounded corners for buttons and cards throughout." },
];
const DENSITY_PRESETS = [
  { label: "Compact", text: "Make the spacing/padding throughout tighter and more compact." },
  { label: "Cozy", text: "Use balanced, comfortable spacing/padding throughout." },
  { label: "Spacious", text: "Make the spacing/padding throughout more generous and airy." },
];
const FONT_PRESETS = [
  { label: "Small", text: "Reduce the base font sizes throughout to feel more compact." },
  { label: "Medium", text: "Use standard, comfortable base font sizes throughout." },
  { label: "Large", text: "Increase the base font sizes throughout for better readability." },
];

export function FeedbackPanel({ run, runId, activeScreenName, selectedElement, onClearSelectedElement, onSubmitted }) {
  const [instruction, setInstruction] = useState("");
  const [scope, setScope] = useState("screen");
  const [file, setFile] = useState(null);
  const [sending, setSending] = useState(false);
  const fileRef = useRef(null);

  const hasWireframes = run?.wireframes?.length > 0;
  const feedbackLog = run?.feedback_log || [];
  const pending = feedbackLog.some((f) => f.status === "running");

  const appendPreset = (text) => setInstruction((prev) => (prev ? `${prev} ${text}` : text));

  const handleSubmit = async () => {
    if (!instruction.trim()) return;
    setSending(true);
    try {
      await submitFeedback(runId, {
        instruction,
        scope,
        screenName: scope !== "all" ? activeScreenName : null,
        file,
        elementContext: selectedElement || null,
      });
      setInstruction("");
      setFile(null);
      onClearSelectedElement?.();
      onSubmitted?.();
      toast.success("Feedback sent to Super Agent");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to send feedback");
    } finally {
      setSending(false);
    }
  };

  if (!hasWireframes) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-xs p-6 text-center" data-testid="feedback-panel-empty">
        Generate wireframes first, then come back here to give feedback or upload a reference to refine them.
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" data-testid="feedback-panel">
      <div className="p-4 border-b border-border space-y-3 overflow-y-auto">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Feedback / Instruction</p>

        {selectedElement && (
          <div className="flex items-start gap-2 border border-secondary/50 bg-secondary/5 p-2" data-testid="selected-element-chip">
            <p className="text-[10px] text-secondary flex-1 font-mono break-all">Selected: {selectedElement}</p>
            <button data-testid="clear-selected-element" onClick={onClearSelectedElement} className="text-muted-foreground hover:text-white shrink-0">
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        <Textarea
          data-testid="feedback-instruction-input"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          placeholder={`e.g. "Make the CTA button more prominent" or "Match this reference layout"`}
          className="rounded-none bg-transparent border-border font-mono text-xs min-h-[60px]"
        />

        <div>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Quick Adjustments</p>
          <div className="flex flex-wrap gap-1 mb-1">
            {COLOR_PRESETS.map((c) => (
              <button
                key={c.name}
                data-testid={`preset-color-${c.name.toLowerCase()}`}
                title={c.name}
                onClick={() => appendPreset(`Use ${c.name} (${c.hex}) as the primary accent color throughout.`)}
                className="w-5 h-5 border border-border shrink-0"
                style={{ backgroundColor: c.hex }}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-1 mb-1">
            {ROUNDNESS_PRESETS.map((p) => (
              <button key={p.label} data-testid={`preset-roundness-${p.label.toLowerCase()}`} onClick={() => appendPreset(p.text)} className="text-[9px] uppercase tracking-wide border border-border px-1.5 py-0.5 text-muted-foreground hover:text-white">
                {p.label}
              </button>
            ))}
            {DENSITY_PRESETS.map((p) => (
              <button key={p.label} data-testid={`preset-density-${p.label.toLowerCase()}`} onClick={() => appendPreset(p.text)} className="text-[9px] uppercase tracking-wide border border-border px-1.5 py-0.5 text-muted-foreground hover:text-white">
                {p.label}
              </button>
            ))}
            {FONT_PRESETS.map((p) => (
              <button key={p.label} data-testid={`preset-font-${p.label.toLowerCase()}`} onClick={() => appendPreset(p.text)} className="text-[9px] uppercase tracking-wide border border-border px-1.5 py-0.5 text-muted-foreground hover:text-white">
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex border border-border">
          <button
            data-testid="feedback-scope-screen"
            onClick={() => setScope("screen")}
            className={`flex-1 text-[10px] uppercase tracking-wide py-1.5 transition-colors ${scope === "screen" ? "bg-primary text-black" : "text-muted-foreground hover:text-white"}`}
          >
            This Screen{activeScreenName ? ` (${activeScreenName})` : ""}
          </button>
          <button
            data-testid="feedback-scope-all"
            onClick={() => setScope("all")}
            className={`flex-1 text-[10px] uppercase tracking-wide py-1.5 transition-colors ${scope === "all" ? "bg-primary text-black" : "text-muted-foreground hover:text-white"}`}
          >
            All Screens
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".html,.css,.txt,image/*"
          data-testid="feedback-file-input"
          className="hidden"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />
        <button
          data-testid="feedback-attach-button"
          onClick={() => fileRef.current?.click()}
          className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-secondary hover:text-white transition-colors"
        >
          <Paperclip className="w-3 h-3" /> {file ? file.name : "Attach template/reference"}
        </button>
        <Button
          data-testid="feedback-submit-button"
          onClick={handleSubmit}
          disabled={sending || pending || !instruction.trim()}
          className="w-full rounded-none bg-secondary text-black hover:bg-white font-chivo font-bold uppercase tracking-wide text-xs gap-2 disabled:opacity-40"
        >
          {sending || pending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
          {pending ? "Super Agent Working..." : "Send To Super Agent"}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3" data-testid="feedback-log">
        {feedbackLog.length === 0 && (
          <p className="text-[11px] text-muted-foreground">No feedback sent yet.</p>
        )}
        {[...feedbackLog].reverse().map((f, i) => (
          <div key={f.id} className="border border-border p-2.5" data-testid={`feedback-entry-${feedbackLog.length - 1 - i}`}>
            <div className="flex items-start gap-2">
              {f.status === "completed" && <CheckCircle2 className="w-3.5 h-3.5 text-[#34C759] shrink-0 mt-0.5" />}
              {f.status === "error" && <XCircle className="w-3.5 h-3.5 text-destructive shrink-0 mt-0.5" />}
              {f.status === "running" && <Loader2 className="w-3.5 h-3.5 text-secondary animate-spin shrink-0 mt-0.5" />}
              <p className="text-[11px] text-white flex-1">{f.instruction}</p>
            </div>
            <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wide">
              Scope: {f.scope === "screen" ? f.screen_name || "screen" : "all screens"}
            </p>
            {f.element_context && <p className="text-[10px] text-secondary mt-1 font-mono break-all">Element: {f.element_context}</p>}
            {f.agent_name && (
              <p className="text-[10px] mt-1.5">
                <span className={`font-bold ${f.is_new_agent ? "text-primary" : "text-secondary"}`}>
                  {f.is_new_agent ? `NEW AGENT: ${f.agent_name}` : f.agent_name}
                </span>
              </p>
            )}
            {f.reasoning && <p className="text-[10px] text-muted-foreground mt-1 leading-relaxed">{f.reasoning}</p>}
            {f.error && <p className="text-[10px] text-destructive mt-1">Error: {f.error}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
