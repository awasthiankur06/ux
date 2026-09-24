import { useEffect, useRef, useState } from "react";
import { getRun } from "@/lib/api";

export function useRunPolling(runId, resumeKey = 0, onNotFound) {
  const [run, setRun] = useState(null);
  const activeRef = useRef(true);

  useEffect(() => {
    activeRef.current = true;
    if (!runId) {
      setRun(null);
      return;
    }

    const poll = async () => {
      try {
        const data = await getRun(runId);
        if (!activeRef.current) return;
        setRun(data);
        const feedbackPending = (data.feedback_log || []).some((f) => f.status === "running");
        if (feedbackPending || !["completed", "error", "awaiting_review"].includes(data.status)) {
          setTimeout(poll, 1800);
        }
      } catch (e) {
        if (e?.response?.status === 404) {
          onNotFound?.();
          return;
        }
        console.error("poll failed", e);
        if (activeRef.current) setTimeout(poll, 3000);
      }
    };
    poll();

    return () => {
      activeRef.current = false;
    };
  }, [runId, resumeKey, onNotFound]);

  return run;
}
