import { useCallback, useEffect, useState } from "react";
import ReactFlow, { Background, Controls, addEdge, applyNodeChanges, applyEdgeChanges, MarkerType, Handle, Position } from "reactflow";
import "reactflow/dist/style.css";
import { getActiveFlow, updateActiveFlow, getAgents } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Save, Lock } from "lucide-react";

const CONDITIONS = ["always", "requires_srs", "requires_url"];

function AgentNode({ data }) {
  return (
    <div className={`border px-3 py-2 text-[11px] font-mono bg-[#111214] min-w-[150px] ${data.condition !== "always" ? "border-secondary" : "border-primary"}`}>
      <Handle type="target" position={Position.Left} style={{ background: "#00E5FF" }} />
      <div className="font-bold text-white">{data.agent_name}</div>
      <div className="text-[9px] text-muted-foreground uppercase mt-0.5">{data.condition}</div>
      <Handle type="source" position={Position.Right} style={{ background: "#00E5FF" }} />
    </div>
  );
}

function FixedNode({ data }) {
  return (
    <div className="border border-dashed border-muted-foreground/50 px-3 py-2 text-[11px] font-mono bg-[#0d0d0e] min-w-[150px] opacity-80">
      <Handle type="target" position={Position.Left} style={{ background: "#666" }} />
      <div className="font-bold text-muted-foreground flex items-center gap-1"><Lock className="w-2.5 h-2.5" />{data.agent_name}</div>
      <div className="text-[9px] text-muted-foreground/70 mt-0.5">{data.caption}</div>
      <Handle type="source" position={Position.Right} style={{ background: "#666" }} />
    </div>
  );
}

const nodeTypes = { agentNode: AgentNode, fixedNode: FixedNode };

const FIXED_NODES = [
  { id: "fixed-super", type: "fixedNode", position: { x: -260, y: 160 }, data: { agent_name: "SUPER_AGENT", caption: "Entry point - always runs first" } },
  { id: "fixed-wireframe", type: "fixedNode", position: { x: 720, y: 40 }, data: { agent_name: "WIREFRAME_GENERATOR", caption: "Standard UX: Generate Wireframes" } },
  { id: "fixed-router", type: "fixedNode", position: { x: 1000, y: 40 }, data: { agent_name: "FEEDBACK_ROUTER", caption: "Standard UX: Feedback submissions" } },
  { id: "fixed-gov-analyst", type: "fixedNode", position: { x: 720, y: 300 }, data: { agent_name: "GOV_COMPLIANCE_ANALYST", caption: "Gov mode: after editable flow" } },
  { id: "fixed-dbi-generator", type: "fixedNode", position: { x: 1000, y: 300 }, data: { agent_name: "DBIM_COMPONENT_GENERATOR", caption: "Gov mode: Generate Wireframes" } },
  { id: "fixed-dbi-validator", type: "fixedNode", position: { x: 1280, y: 300 }, data: { agent_name: "DBIM_GIGW_VALIDATOR", caption: "Gov mode: deterministic pre-check" } },
  { id: "fixed-export", type: "fixedNode", position: { x: 1280, y: 40 }, data: { agent_name: "EXPORT_AGENT", caption: "Triggered by Finalize & Export" } },
];

function fixedEdgesFor(editableNodeIds) {
  const edges = [
    { id: "fe-wireframe-router", source: "fixed-wireframe", target: "fixed-router", style: { strokeDasharray: "4 4" } },
    { id: "fe-wireframe-export", source: "fixed-wireframe", target: "fixed-export", style: { strokeDasharray: "4 4" } },
    { id: "fe-gov-generator", source: "fixed-gov-analyst", target: "fixed-dbi-generator", style: { strokeDasharray: "4 4" } },
    { id: "fe-gov-validator", source: "fixed-dbi-generator", target: "fixed-dbi-validator", style: { strokeDasharray: "4 4" } },
    { id: "fe-gov-export", source: "fixed-dbi-validator", target: "fixed-export", style: { strokeDasharray: "4 4" } },
  ];
  editableNodeIds.forEach((id, i) => {
    edges.push({ id: `fe-super-${i}`, source: "fixed-super", target: id, style: { strokeDasharray: "4 4" } });
    edges.push({ id: `fe-${id}-wireframe`, source: id, target: "fixed-wireframe", style: { strokeDasharray: "4 4" } });
    edges.push({ id: `fe-${id}-gov`, source: id, target: "fixed-gov-analyst", style: { strokeDasharray: "4 4" } });
  });
  return edges;
}

export function FlowCanvas() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [agentsList, setAgentsList] = useState([]);

  useEffect(() => {
    (async () => {
      const [flow, agentDocs] = await Promise.all([getActiveFlow(), getAgents()]);
      setAgentsList(agentDocs);
      const editable = flow.nodes.map((n) => ({ id: n.id, type: "agentNode", position: n.position, data: { agent_name: n.agent_name, condition: n.condition } }));
      const editableEdges = flow.edges.map((e) => ({ id: e.id, source: e.source, target: e.target, markerEnd: { type: MarkerType.ArrowClosed } }));
      setNodes([...editable, ...FIXED_NODES]);
      setEdges([...editableEdges, ...fixedEdgesFor(editable.map((n) => n.id))]);
    })();
  }, []);

  const onNodesChange = useCallback((changes) => setNodes((nds) => applyNodeChanges(changes, nds)), []);
  const onEdgesChange = useCallback((changes) => setEdges((eds) => applyEdgeChanges(changes, eds)), []);
  const onConnect = useCallback((connection) => setEdges((eds) => addEdge({ ...connection, id: `e-${Date.now()}`, markerEnd: { type: MarkerType.ArrowClosed } }, eds)), []);

  const addNode = (agentName) => {
    const id = `n-${Date.now()}`;
    setNodes((nds) => [...nds, { id, type: "agentNode", position: { x: 120 + (nds.length % 4) * 40, y: 100 + nds.length * 60 }, data: { agent_name: agentName, condition: "always" } }]);
  };

  const cycleCondition = (nodeId) => {
    setNodes((nds) => nds.map((n) => {
      if (n.id !== nodeId || n.type !== "agentNode") return n;
      const idx = CONDITIONS.indexOf(n.data.condition);
      return { ...n, data: { ...n.data, condition: CONDITIONS[(idx + 1) % CONDITIONS.length] } };
    }));
  };

  const deleteNode = (nodeId) => {
    if (nodeId.startsWith("fixed-")) return;
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
  };

  const save = async () => {
    try {
      const editableNodes = nodes.filter((n) => n.type === "agentNode");
      const editableIds = new Set(editableNodes.map((n) => n.id));
      const editableEdges = edges.filter((e) => editableIds.has(e.source) && editableIds.has(e.target));
      const payload = {
        nodes: editableNodes.map((n) => ({ id: n.id, agent_name: n.data.agent_name, condition: n.data.condition, position: n.position })),
        edges: editableEdges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
      };
      await updateActiveFlow(payload);
      toast.success("Orchestration flow saved - applies to your next run");
    } catch (e) {
      toast.error("Failed to save flow");
    }
  };

  const usedNames = new Set(nodes.filter((n) => n.type === "agentNode").map((n) => n.data.agent_name));
  const availableAgents = agentsList.filter((a) => !usedNames.has(a.name) && !["SUPER_AGENT", "FEEDBACK_ROUTER", "WIREFRAME_GENERATOR", "EXPORT_AGENT", "GOV_COMPLIANCE_ANALYST", "DBIM_COMPONENT_GENERATOR", "DBIM_GIGW_VALIDATOR"].includes(a.name));

  return (
    <div className="h-full flex flex-col" data-testid="flow-canvas">
      <div className="flex items-center justify-between p-3 border-b border-border shrink-0">
        <select
          data-testid="flow-add-node-select"
          onChange={(e) => { if (e.target.value) { addNode(e.target.value); e.target.value = ""; } }}
          className="bg-transparent border border-border text-[11px] px-2 py-1 text-white"
        >
          <option value="">+ Add Node...</option>
          {availableAgents.map((a) => <option key={a.id} value={a.name}>{a.name}</option>)}
        </select>
        <Button data-testid="save-flow-button" onClick={save} className="rounded-none bg-primary text-black hover:bg-white text-[11px] uppercase font-bold gap-1.5">
          <Save className="w-3.5 h-3.5" /> Save Flow
        </Button>
      </div>
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          onNodeDoubleClick={(e, node) => cycleCondition(node.id)}
          onNodeContextMenu={(e, node) => { e.preventDefault(); deleteNode(node.id); }}
          fitView
        >
          <Background color="#262626" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
      <p className="text-[10px] text-muted-foreground p-2 border-t border-border shrink-0">
        Solid nodes are the editable discovery flow (double-click to cycle condition, right-click to delete, drag to connect). Dashed nodes are fixed runtime stages: the upper route is Standard UX; the lower route runs only when Gov Compliance - Design Pre-check is selected. Fixed nodes are not part of the saved graph.
      </p>
    </div>
  );
}
