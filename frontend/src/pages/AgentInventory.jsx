import { useState } from "react";
import { Link } from "react-router-dom";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { AgentEditorPanel } from "@/components/agents/AgentEditorPanel";
import { FlowCanvas } from "@/components/agents/FlowCanvas";
import { LlmSettingsPanel } from "@/components/agents/LlmSettingsPanel";
import { ArrowLeft, Cpu } from "lucide-react";

export default function AgentInventory() {
  const [tab, setTab] = useState("agents");

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden" data-testid="agent-inventory-page">
      <div className="h-12 border-b border-border flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-primary" />
          <span className="font-chivo font-bold text-sm tracking-tight">AGENT_INVENTORY</span>
        </div>
        <Link data-testid="back-to-studio-link" to="/" className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground hover:text-primary transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back To Studio
        </Link>
      </div>
      <Tabs value={tab} onValueChange={setTab} className="flex-1 flex flex-col overflow-hidden">
        <TabsList className="rounded-none bg-transparent border-b border-border justify-start h-10 px-2 shrink-0">
          <TabsTrigger data-testid="tab-agents" value="agents" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
            Agents
          </TabsTrigger>
          <TabsTrigger data-testid="tab-orchestration-flow" value="flow" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
            Orchestration Flow
          </TabsTrigger>
          <TabsTrigger data-testid="tab-llm-settings" value="settings" className="rounded-none text-[11px] uppercase tracking-wide data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none">
            LLM Settings
          </TabsTrigger>
        </TabsList>
        <TabsContent value="agents" className="flex-1 overflow-hidden m-0"><AgentEditorPanel /></TabsContent>
        <TabsContent value="flow" className="flex-1 overflow-hidden m-0"><FlowCanvas /></TabsContent>
        <TabsContent value="settings" className="flex-1 overflow-hidden m-0"><LlmSettingsPanel /></TabsContent>
      </Tabs>
    </div>
  );
}
