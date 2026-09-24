import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, ArrowDown, Trash2, Plus, Hammer, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function FlowDiagram({ businessFlow, editable, onGenerate, generating }) {
  const [steps, setSteps] = useState([]);

  useEffect(() => {
    if (!businessFlow) {
      setSteps([]);
      return;
    }
    if (businessFlow.happy_path && steps.length === 0) setSteps(businessFlow.happy_path);
  }, [businessFlow, steps.length]);

  if (!businessFlow) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-xs" data-testid="flow-diagram-empty">
        Happy-path flow will render here once the Business Process Analyst completes.
      </div>
    );
  }

  const update = (i, field, value) => {
    setSteps((prev) => prev.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));
  };

  const move = (i, dir) => {
    setSteps((prev) => {
      const next = [...prev];
      const target = i + dir;
      if (target < 0 || target >= next.length) return prev;
      [next[i], next[target]] = [next[target], next[i]];
      return next;
    });
  };

  const remove = (i) => setSteps((prev) => prev.filter((_, idx) => idx !== i));

  const addStep = () =>
    setSteps((prev) => [...prev, { step: prev.length + 1, screen_name: "New Screen", description: "", key_actions: [], components: [] }]);

  return (
    <div className="p-6 overflow-y-auto h-full" data-testid="flow-diagram">
      {businessFlow.business_goals?.length > 0 && (
        <div className="mb-6 border border-border p-3">
          <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1.5">Business Goals</p>
          <ul className="text-xs text-muted-foreground space-y-1">
            {businessFlow.business_goals.map((g, i) => (
              <li key={i}>— {g}</li>
            ))}
          </ul>
        </div>
      )}

      {editable && (
        <div className="mb-4 flex items-center justify-between border border-secondary/40 bg-secondary/5 p-2.5">
          <p className="text-[11px] text-secondary">Review & tweak the happy path below, then generate wireframes.</p>
          <Button
            data-testid="generate-wireframes-button"
            onClick={() => onGenerate(steps)}
            disabled={generating || steps.length === 0}
            className="rounded-none bg-primary text-black hover:bg-white font-chivo font-bold uppercase tracking-wide text-[11px] gap-2 shrink-0 disabled:opacity-40"
          >
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Hammer className="w-3.5 h-3.5" />}
            {generating ? "Generating..." : "Generate Wireframes"}
          </Button>
        </div>
      )}

      <div className="relative">
        {steps.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: i * 0.06 }}
            className="flex gap-4 pb-8 relative"
            data-testid={`flow-step-${i}`}
          >
            {i < steps.length - 1 && <div className="absolute left-[15px] top-[32px] bottom-0 w-px bg-border" />}
            <div className="w-8 h-8 rounded-none border border-primary text-primary flex items-center justify-center text-xs font-bold shrink-0 bg-background z-10">
              {i + 1}
            </div>
            <div className="pt-0.5 flex-1 min-w-0">
              {editable ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Input
                      data-testid={`flow-step-name-input-${i}`}
                      value={step.screen_name}
                      onChange={(e) => update(i, "screen_name", e.target.value)}
                      className="rounded-none bg-transparent border-border font-chivo font-bold text-sm h-8"
                    />
                    <button data-testid={`flow-step-up-${i}`} onClick={() => move(i, -1)} className="text-muted-foreground hover:text-white shrink-0">
                      <ArrowUp className="w-3.5 h-3.5" />
                    </button>
                    <button data-testid={`flow-step-down-${i}`} onClick={() => move(i, 1)} className="text-muted-foreground hover:text-white shrink-0">
                      <ArrowDown className="w-3.5 h-3.5" />
                    </button>
                    <button data-testid={`flow-step-delete-${i}`} onClick={() => remove(i)} className="text-destructive hover:text-white shrink-0">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <Textarea
                    data-testid={`flow-step-description-input-${i}`}
                    value={step.description}
                    onChange={(e) => update(i, "description", e.target.value)}
                    className="rounded-none bg-transparent border-border font-mono text-xs min-h-[50px]"
                  />
                </div>
              ) : (
                <>
                  <p className="font-chivo font-bold text-sm text-white">{step.screen_name}</p>
                  <p className="text-xs text-muted-foreground mt-1">{step.description}</p>
                </>
              )}
              {step.key_actions?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {step.key_actions.map((a, j) => (
                    <span key={j} className="text-[10px] border border-border px-1.5 py-0.5 text-secondary uppercase tracking-wide">
                      {a}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {editable && (
        <button
          data-testid="flow-step-add-button"
          onClick={addStep}
          className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-secondary hover:text-white transition-colors mt-1"
        >
          <Plus className="w-3.5 h-3.5" /> Add Screen
        </button>
      )}
    </div>
  );
}
