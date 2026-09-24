import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { createRun, uploadSrsFile, updateHappyPath, generateWireframes } from "@/lib/api";
import { useRunPolling } from "@/hooks/useRunPolling";
import { InputPanel } from "@/components/studio/InputPanel";
import { OrchestratorLog } from "@/components/studio/OrchestratorLog";
import { FlowDiagram } from "@/components/studio/FlowDiagram";
import { WirePreview } from "@/components/studio/WirePreview";
import { UxRatingReport } from "@/components/studio/UxRatingReport";
import { ExportPanel } from "@/components/studio/ExportPanel";
import { FeedbackPanel } from "@/components/studio/FeedbackPanel";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { RotateCcw, Cpu, Link2, Bot } from "lucide-react";

export default function Studio() {
  const { runId: paramRunId } = useParams();
  const navigate = useNavigate();

  const [srsText, setSrsText] = useState("");
  const [url, setUrl] = useState("");
  const [crawlDepth, setCrawlDepth] = useState("single");
  const [brandReference, setBrandReference] = useState(null);
  const [brandFileName, setBrandFileName] = useState(null);
  const [runId, setRunId] = useState(paramRunId || null);
  const [resumeKey, setResumeKey] = useState(0);
  const [centerTab, setCenterTab] = useState("render");
  const [rightTab, setRightTab] = useState("rating");
  const [activeScreenIdx, setActiveScreenIdx] = useState(0);
  const [generatingWireframes, setGeneratingWireframes] = useState(false);
  const [commentMode, setCommentMode] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);
  const handleRunNotFound = useCallback(() => {
    toast.error("Run not found - starting fresh");
    setRunId(null);
    navigate("/");
  }, [navigate]);
  const run = useRunPolling(runId, resumeKey, handleRunNotFound);

  useEffect(() => {
    if (run?.status === "awaiting_review" && !generatingWireframes) setCenterTab("flow");
  }, [run?.status]);

  useEffect(() => {
    if (run?.status === "completed" || run?.status === "error") setGeneratingWireframes(false);
  }, [run?.status]);

  const handleFileSelect = async (file) => {
    try {
      const { text } = await uploadSrsFile(file);
      setSrsText(text);
      toast.success("SRS text extracted from file");
    } catch (e) {
      toast.error("Failed to extract file text");
    }
  };

  const handleBrandFileSelect = async (file) => {
    try {
      const { text } = await uploadSrsFile(file);
      setBrandReference(text);
      setBrandFileName(file.name);
      toast.success("Brand reference loaded");
    } catch (e) {
      toast.error("Failed to read brand reference");
    }
  };

  const handleSubmit = async () => {
    try {
      const { run_id } = await createRun({ srs_text: srsText || null, url: url || null, crawl_depth: crawlDepth, brand_reference: brandReference });
      setRunId(run_id);
      setCenterTab("render");
      setGeneratingWireframes(false);
      setActiveScreenIdx(0);
      setCommentMode(false);
      setSelectedElement(null);
      navigate(`/run/${run_id}`);
      toast.success("Orchestrator initialized");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to start run");
    }
  };

  const handleGenerateWireframes = async (steps) => {
    setGeneratingWireframes(true);
    try {
      await updateHappyPath(runId, steps);
      await generateWireframes(runId);
      setCenterTab("render");
      setActiveScreenIdx(0);
      setResumeKey((k) => k + 1);
    } catch (e) {
      toast.error("Failed to start wireframe generation");
      setGeneratingWireframes(false);
    }
  };

  const handleElementSelected = (descriptor) => {
    setSelectedElement(descriptor);
    setCommentMode(false);
    setRightTab("feedback");
  };

  const copyShareLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/run/${runId}`);
    toast.success("Share link copied");
  };

  const reset = () => {
    setRunId(null);
    setSrsText("");
    setUrl("");
    setBrandReference(null);
    setBrandFileName(null);
    setGeneratingWireframes(false);
    setCenterTab("render");
    setActiveScreenIdx(0);
    setCommentMode(false);
    setSelectedElement(null);
    navigate("/");
  };

  const totalStages = run ? 1 + (run.orchestrator_plan?.agents?.length || 0) : 1;
  const completedCount = new Set((run?.stage_log || []).filter((l) => l.status === "completed").map((l) => l.stage)).size;
  const progress = run ? Math.min(100, (completedCount / totalStages) * 100) : 0;

  return (
    <div className="min-h-screen lg:h-screen w-screen flex flex-col lg:overflow-hidden">
      <div className="h-12 border-b border-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-primary" />
          <span className="font-chivo font-bold text-sm tracking-tight" data-testid="app-title">UX_ORCHESTRATOR</span>
          <span className="text-[10px] text-muted-foreground tracking-[0.2em] uppercase hidden sm:inline">// Agentic Design Studio</span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            data-testid="agent-inventory-link"
            to="/agents"
            className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground hover:text-secondary transition-colors"
          >
            <Bot className="w-3.5 h-3.5" /> Agent Inventory
          </Link>
          {run && (
            <div className="flex items-center gap-4">
            <button
              data-testid="copy-share-link-button"
              onClick={copyShareLink}
              className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground hover:text-secondary transition-colors"
            >
              <Link2 className="w-3.5 h-3.5" /> Share Link
            </button>
            <button
              data-testid="new-analysis-button"
              onClick={reset}
              className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground hover:text-primary transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" /> New Analysis
            </button>
          </div>
        )}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-border lg:overflow-hidden">
        <div className="flex flex-col lg:overflow-hidden lg:col-span-1 min-h-[70vh] lg:min-h-0">
          <InputPanel
            srsText={srsText}
            setSrsText={setSrsText}
            url={url}
            setUrl={setUrl}
            crawlDepth={crawlDepth}
            setCrawlDepth={setCrawlDepth}
            onSubmit={handleSubmit}
            loading={run && !["completed", "error", "awaiting_review"].includes(run.status)}
            onFileSelect={handleFileSelect}
            brandFileName={brandFileName}
            onBrandFileSelect={handleBrandFileSelect}
          />
          {run && (
            <div className="px-4 pt-3">
              <Progress value={progress} className="h-1 rounded-none bg-muted" data-testid="orchestration-progress" />
            </div>
          )}
          <OrchestratorLog run={run} />
        </div>

        <div className="flex flex-col lg:overflow-hidden lg:col-span-2 min-h-[70vh] lg:min-h-0">
          <Tabs value={centerTab} onValueChange={setCenterTab} className="flex flex-col h-full">
            <TabsList className="rounded-none bg-transparent border-b border-border justify-start h-9 px-2 shrink-0">
              <TabsTrigger data-testid="tab-flow-diagram" value="flow" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
                Flow Diagram
              </TabsTrigger>
              <TabsTrigger data-testid="tab-live-render" value="render" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
                Live Render
              </TabsTrigger>
            </TabsList>
            <TabsContent value="flow" className="flex-1 lg:overflow-hidden m-0">
              <FlowDiagram
                businessFlow={run?.business_flow}
                editable={run?.status === "awaiting_review" && !generatingWireframes}
                generating={generatingWireframes}
                onGenerate={handleGenerateWireframes}
              />
            </TabsContent>
            <TabsContent value="render" className="flex-1 lg:overflow-hidden m-0">
              <WirePreview
                wireframes={run?.wireframes}
                activeIdx={activeScreenIdx}
                setActiveIdx={setActiveScreenIdx}
                commentMode={commentMode}
                setCommentMode={setCommentMode}
                onElementSelected={handleElementSelected}
              />
            </TabsContent>
          </Tabs>
        </div>

        <div className="flex flex-col lg:overflow-hidden lg:col-span-1 min-h-[70vh] lg:min-h-0">
          <Tabs value={rightTab} onValueChange={setRightTab} className="flex flex-col h-full">
            <TabsList className="rounded-none bg-transparent border-b border-border justify-start h-9 px-2 shrink-0">
              <TabsTrigger data-testid="tab-ux-rating" value="rating" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
                UX Rating
              </TabsTrigger>
              <TabsTrigger data-testid="tab-feedback" value="feedback" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
                Feedback
              </TabsTrigger>
              <TabsTrigger data-testid="tab-export" value="export" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
                Export
              </TabsTrigger>
            </TabsList>
            <TabsContent value="rating" className="flex-1 lg:overflow-hidden m-0">
              <UxRatingReport uxRating={run?.ux_rating} />
            </TabsContent>
            <TabsContent value="feedback" className="flex-1 lg:overflow-hidden m-0">
              <FeedbackPanel
                run={run}
                runId={runId}
                activeScreenName={run?.wireframes?.[activeScreenIdx]?.screen_name}
                selectedElement={selectedElement}
                onClearSelectedElement={() => setSelectedElement(null)}
                onSubmitted={() => setResumeKey((k) => k + 1)}
              />
            </TabsContent>
            <TabsContent value="export" className="flex-1 lg:overflow-hidden m-0">
              <ExportPanel run={run} runId={runId} />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
