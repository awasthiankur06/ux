import { useEffect, useState } from "react";
import { getAgents, createAgent, updateAgent, deleteAgent, getModelChoices } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { Plus, Trash2, Save, Bot } from "lucide-react";

export function AgentEditorPanel() {
  const [agentsList, setAgentsList] = useState([]);
  const [modelChoices, setModelChoices] = useState({});
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(null);
  const [creating, setCreating] = useState(false);

  const load = async () => {
    const [docs, choices] = await Promise.all([getAgents(), getModelChoices()]);
    setAgentsList(docs);
    setModelChoices(choices);
  };
  useEffect(() => { load(); }, []);

  const selectAgent = (a) => {
    setSelectedId(a.id);
    setCreating(false);
    setForm({ name: a.name, description: a.description || "", system_prompt: a.system_prompt || "", model_provider: a.model_provider || "", model_name: a.model_name || "" });
  };

  const startCreate = () => {
    setCreating(true);
    setSelectedId(null);
    setForm({ name: "", description: "", system_prompt: "", model_provider: "", model_name: "" });
  };

  const save = async () => {
    try {
      if (creating) {
        await createAgent({ name: form.name, description: form.description, system_prompt: form.system_prompt, model_provider: form.model_provider || null, model_name: form.model_name || null });
        toast.success("Agent created");
        setCreating(false);
      } else {
        await updateAgent(selectedId, { description: form.description, system_prompt: form.system_prompt, model_provider: form.model_provider, model_name: form.model_name });
        toast.success("Agent updated");
      }
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save agent");
    }
  };

  const remove = async (id) => {
    try {
      await deleteAgent(id);
      toast.success("Agent deleted");
      setSelectedId(null);
      setForm(null);
      await load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to delete agent");
    }
  };

  const providerModels = form?.model_provider ? modelChoices[form.model_provider] || [] : [];
  const selectedAgent = agentsList.find((a) => a.id === selectedId);

  return (
    <div className="h-full grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-border" data-testid="agent-editor-panel">
      <div className="overflow-y-auto p-2 space-y-1">
        <button data-testid="new-agent-button" onClick={startCreate} className="w-full flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-secondary hover:text-white p-2 border border-dashed border-border">
          <Plus className="w-3.5 h-3.5" /> New Agent
        </button>
        {agentsList.map((a) => (
          <button
            key={a.id}
            data-testid={`agent-list-item-${a.name}`}
            onClick={() => selectAgent(a)}
            className={`w-full text-left p-2 border text-[11px] transition-colors ${selectedId === a.id ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-white"}`}
          >
            <div className="flex items-center gap-1.5 font-bold"><Bot className="w-3 h-3" />{a.name}</div>
            <div className="text-[9px] uppercase mt-0.5">
              {a.is_builtin ? "Built-in" : a.is_dynamic ? "Auto-created" : "Custom"} · {a.agent_type}
            </div>
          </button>
        ))}
      </div>

      <div className="md:col-span-2 overflow-y-auto p-4 space-y-3">
        {!form && <p className="text-xs text-muted-foreground">Select an agent to edit, or create a new one.</p>}
        {form && (
          <>
            {creating ? (
              <Input data-testid="agent-name-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value.toUpperCase().replace(/\s+/g, "_") })} placeholder="AGENT_NAME" className="rounded-none bg-transparent border-border font-mono text-xs" />
            ) : (
              <p className="font-chivo font-bold text-white" data-testid="agent-name-display">{form.name}</p>
            )}
            <Input data-testid="agent-description-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Description" className="rounded-none bg-transparent border-border font-mono text-xs" />
            <Textarea data-testid="agent-prompt-input" value={form.system_prompt} onChange={(e) => setForm({ ...form, system_prompt: e.target.value })} placeholder="System prompt..." className="rounded-none bg-transparent border-border font-mono text-xs min-h-[220px]" />

            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Model Override (optional - falls back to global default)</p>
              <div className="flex gap-2">
                <select data-testid="agent-provider-select" value={form.model_provider} onChange={(e) => setForm({ ...form, model_provider: e.target.value, model_name: "" })} className="flex-1 bg-transparent border border-border text-[11px] px-2 py-1.5 text-white">
                  <option value="">Use global default</option>
                  {Object.keys(modelChoices).map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
                <select data-testid="agent-model-select" value={form.model_name} onChange={(e) => setForm({ ...form, model_name: e.target.value })} disabled={!form.model_provider} className="flex-1 bg-transparent border border-border text-[11px] px-2 py-1.5 text-white disabled:opacity-40">
                  <option value="">Default model</option>
                  {providerModels.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>

            <div className="flex gap-2">
              <Button data-testid="save-agent-button" onClick={save} className="rounded-none bg-primary text-black hover:bg-white text-[11px] uppercase font-bold gap-1.5">
                <Save className="w-3.5 h-3.5" /> Save
              </Button>
              {!creating && selectedAgent && !selectedAgent.is_builtin && (
                <Button data-testid="delete-agent-button" onClick={() => remove(selectedId)} className="rounded-none bg-transparent border border-destructive text-destructive hover:bg-destructive hover:text-white text-[11px] uppercase font-bold gap-1.5">
                  <Trash2 className="w-3.5 h-3.5" /> Delete
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
