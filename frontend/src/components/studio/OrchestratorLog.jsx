import { motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

const TAG_COLORS = {
  SUPER_AGENT: "text-primary",
  SRS_ANALYZER: "text-secondary",
  WEB_CRAWLER: "text-secondary",
  BUSINESS_PROCESS_ANALYST: "text-primary",
  UX_CRITIQUE: "text-destructive",
  WIREFRAME_GENERATOR: "text-primary",
};

function StatusIcon({ status }) {
  if (status === "completed") return <CheckCircle2 className="w-3 h-3 text-[#34C759] shrink-0 mt-0.5" />;
  if (status === "error") return <XCircle className="w-3 h-3 text-destructive shrink-0 mt-0.5" />;
  return <Loader2 className="w-3 h-3 text-secondary animate-spin shrink-0 mt-0.5" />;
}

export function OrchestratorLog({ run }) {
  const logs = run?.stage_log || [];

  return (
    <div className="shrink-0 p-4 font-mono text-[11px] leading-relaxed" data-testid="orchestrator-log">
      <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-3">// Super Agent Mission Log</p>
      {logs.length === 0 && (
        <pre className="text-muted-foreground text-[10px] leading-tight">{`
  ┌──────────────────┐
  │  STANDBY MODE    │
  │  awaiting input  │
  └──────────────────┘`}</pre>
      )}
      <div className="space-y-2.5">
        {logs.map((entry, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25 }}
            className="flex gap-2 items-start"
            data-testid={`log-entry-${i}`}
          >
            <StatusIcon status={entry.status} />
            <div>
              <span className={`${TAG_COLORS[entry.label] || "text-white"} font-bold`}>[{entry.label}]</span>{" "}
              <span className="text-muted-foreground">{entry.detail}</span>
            </div>
          </motion.div>
        ))}
      </div>
      {run?.error && (
        <p className="mt-4 text-destructive" data-testid="run-error-message">ERROR: {run.error}</p>
      )}
    </div>
  );
}
