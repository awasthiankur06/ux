import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Studio from "@/pages/Studio";
import AgentInventory from "@/pages/AgentInventory";

function App() {
  return (
    <div className="App bg-background text-foreground">
      <div className="noise-overlay" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Studio />} />
          <Route path="/run/:runId" element={<Studio />} />
          <Route path="/agents" element={<AgentInventory />} />
        </Routes>
      </BrowserRouter>
      <Toaster />
    </div>
  );
}

export default App;
