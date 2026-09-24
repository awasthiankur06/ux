import { useEffect, useState } from "react";
import { getLlmSettings, updateLlmSettings, updateLlmApiKey, deleteLlmApiKey, updateEyIncubatorConfig, getModelChoices } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { ChevronDown, ChevronRight, Save, KeyRound, Trash2 } from "lucide-react";

export function LlmSettingsPanel() {
  const [settings, setSettings] = useState(null);
  const [choices, setChoices] = useState({});
  const [keyInputs, setKeyInputs] = useState({});
  const [eyEndpoint, setEyEndpoint] = useState("");
  const [eyModels, setEyModels] = useState("");
  const [eyApiVersion, setEyApiVersion] = useState("");
  const [showEyConfig, setShowEyConfig] = useState(false);

  const refresh = async () => {
    const [s, c] = await Promise.all([getLlmSettings(), getModelChoices()]);
    setSettings(s);
    setChoices(c);
    const config = s.provider_configs?.ey_incubator || {};
    setEyEndpoint(config.base_url || "");
    setEyModels((config.models || c.ey_incubator || []).join(", "));
    setEyApiVersion(config.api_version || "");
  };

  useEffect(() => {
    refresh();
  }, []);

  if (!settings) return null;

  const save = async () => {
    try {
      await updateLlmSettings({ default_provider: settings.default_provider, default_model: settings.default_model });
      toast.success("Global LLM default updated");
    } catch (e) {
      toast.error("Failed to save settings");
    }
  };

  const saveKey = async (provider) => {
    const apiKey = (keyInputs[provider] || "").trim();
    if (!apiKey) {
      toast.error("Enter an API key first");
      return;
    }
    try {
      const updated = await updateLlmApiKey(provider, apiKey);
      setSettings(updated);
      setKeyInputs((k) => ({ ...k, [provider]: "" }));
      toast.success(`${provider} API key saved`);
    } catch (e) {
      toast.error("Failed to save API key");
    }
  };

  const removeKey = async (provider) => {
    try {
      const updated = await deleteLlmApiKey(provider);
      setSettings(updated);
      toast.success(`${provider} API key removed`);
    } catch (e) {
      toast.error("Failed to remove API key");
    }
  };

  const saveEyConfig = async () => {
    const models = eyModels.split(",").map((model) => model.trim()).filter(Boolean);
    try {
      const updated = await updateEyIncubatorConfig({ base_url: eyEndpoint, models, api_version: eyApiVersion });
      setSettings(updated);
      setChoices(await getModelChoices());
      toast.success("EY Incubator endpoint and models saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save EY Incubator configuration");
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6 max-w-md space-y-8" data-testid="llm-settings-panel">
      <div className="space-y-4">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Global Default Model</p>
        <p className="text-xs text-muted-foreground">Used by any agent that doesn't have its own model override set in the Agent Inventory.</p>
        <div className="flex gap-2">
          <select
            data-testid="global-provider-select"
            value={settings.default_provider}
            onChange={(e) => setSettings({ ...settings, default_provider: e.target.value, default_model: (choices[e.target.value] || [])[0] || "" })}
            className="flex-1 bg-transparent border border-border text-[11px] px-2 py-1.5 text-white"
          >
            {Object.keys(choices).map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <select
            data-testid="global-model-select"
            value={settings.default_model}
            onChange={(e) => setSettings({ ...settings, default_model: e.target.value })}
            className="flex-1 bg-transparent border border-border text-[11px] px-2 py-1.5 text-white"
          >
            {(choices[settings.default_provider] || []).map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <Button data-testid="save-global-settings-button" onClick={save} className="rounded-none bg-primary text-black hover:bg-white text-[11px] uppercase font-bold gap-1.5">
          <Save className="w-3.5 h-3.5" /> Save
        </Button>
      </div>

      <div className="space-y-4 pt-2 border-t border-border">
        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-1.5 pt-4">
          <KeyRound className="w-3 h-3" /> Provider API Keys
        </p>
        <p className="text-xs text-muted-foreground">
          {settings.has_platform_key
            ? "Keys are optional here — without one, calls fall back to the Emergent platform's managed key (only works inside Emergent)."
            : "No platform-managed key detected. Add your own key per provider below for calls to work."}
        </p>
        {Object.keys(choices).map((provider) => {
          const masked = settings.api_keys?.[provider];
          return (
            <div key={provider} className="space-y-1.5" data-testid={`api-key-row-${provider}`}>
              <div className="flex items-center justify-between">
                <span className="text-[11px] uppercase font-bold text-white">{provider}</span>
                {masked ? (
                  <span className="text-[10px] font-mono text-primary" data-testid={`api-key-masked-${provider}`}>{masked} saved</span>
                ) : (
                  <span className="text-[10px] font-mono text-muted-foreground">not set</span>
                )}
              </div>
              <div className="flex gap-2">
                  <Input
                    data-testid={`api-key-input-${provider}`}
                    type="password"
                    placeholder={masked ? "Enter new key to replace..." : `${provider} API key (sk-...)`}
                    value={keyInputs[provider] || ""}
                    onChange={(e) => setKeyInputs((k) => ({ ...k, [provider]: e.target.value }))}
                    className="flex-1 rounded-none bg-transparent border-border text-[11px] h-8"
                  />
                  <Button
                    data-testid={`api-key-save-${provider}`}
                    onClick={() => saveKey(provider)}
                    className="rounded-none bg-primary text-black hover:bg-white text-[11px] h-8 px-3"
                  >
                    Save
                  </Button>
                  {masked && (
                    <Button
                      data-testid={`api-key-remove-${provider}`}
                      onClick={() => removeKey(provider)}
                      variant="outline"
                      className="rounded-none h-8 px-2 border-border"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-2 border-t border-border">
        <button
          type="button"
          data-testid="toggle-ey-incubator-config"
          onClick={() => setShowEyConfig((visible) => !visible)}
          className="w-full flex items-center gap-1.5 pt-4 text-[10px] uppercase tracking-[0.2em] text-muted-foreground hover:text-secondary transition-colors"
        >
          {showEyConfig ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          Advanced / Provider Configuration
        </button>
        {showEyConfig && (
          <div className="space-y-4 pt-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">EY Incubator Endpoint</p>
            <p className="text-xs text-muted-foreground">EY Incubator uses Azure-style deployments. Enter its base endpoint, API version, and deployment names exactly as supplied by EY.</p>
            <Input data-testid="ey-incubator-endpoint-input" value={eyEndpoint} onChange={(e) => setEyEndpoint(e.target.value)} placeholder="https://your-ey-endpoint" className="rounded-none bg-transparent border-border text-[11px] h-8" />
            <Input data-testid="ey-incubator-api-version-input" value={eyApiVersion} onChange={(e) => setEyApiVersion(e.target.value)} placeholder="API version, e.g. 2024-02-15-preview" className="rounded-none bg-transparent border-border text-[11px] h-8" />
            <Input data-testid="ey-incubator-models-input" value={eyModels} onChange={(e) => setEyModels(e.target.value)} placeholder="Deployment names, comma-separated" className="rounded-none bg-transparent border-border text-[11px] h-8" />
            <Button data-testid="save-ey-incubator-config-button" onClick={saveEyConfig} className="rounded-none bg-secondary text-black hover:bg-white text-[11px] uppercase font-bold gap-1.5">
              <Save className="w-3.5 h-3.5" /> Save EY Configuration
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
