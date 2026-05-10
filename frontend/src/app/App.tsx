import { useState } from "react";
import { LandingPage } from "./components/LandingPage";
import { FindingsList } from "./components/FindingsList";
import { GraphExplorer } from "./components/GraphExplorer";
import { NodeDetail } from "./components/NodeDetail";
import { BlastRadius } from "./components/BlastRadius";

export default function App() {
  const [showDashboard, setShowDashboard] = useState(false);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showNodeDetail, setShowNodeDetail] = useState(true);

  if (!showDashboard) {
    return <LandingPage onStart={() => setShowDashboard(true)} />;
  }

  return (
    <div className="size-full bg-[#0D0D0D] flex flex-col">
      <header
        className="h-[48px] border-b border-[#1F1F1F] flex items-center justify-between px-4"
        style={{ fontFamily: "IBM Plex Mono" }}
      >
        <div className="text-[14px]" style={{ color: "#E8E8E8" }}>
          HyperAD
        </div>
        <div className="text-[12px]" style={{ color: "#6B6B6B" }}>
          Last scan: 14m ago
        </div>
        <button
          className="px-4 py-1.5 border border-[#D4A853] text-[13px] rounded-[4px] transition-colors hover:bg-[#D4A853] hover:text-[#0D0D0D]"
          style={{ fontFamily: "Inter", color: "#D4A853" }}
        >
          Run Scan
        </button>
      </header>

      <div className="flex-1 flex overflow-hidden relative">
        <FindingsList onFindingSelect={() => {}} />
        <GraphExplorer
          onNodeSelect={(node) => {
            setSelectedNode(node);
            setSelectedNodeId(node.id);
          }}
        />

        <button
          onClick={() => setShowNodeDetail(!showNodeDetail)}
          className="absolute top-4 right-4 px-3 py-1.5 border border-[#2A2A2A] text-[11px] rounded-[4px] transition-colors hover:border-[#6B6B6B] z-10"
          style={{ fontFamily: "Inter", color: "#6B6B6B" }}
        >
          {showNodeDetail ? "Hide Details" : "Show Details"}
        </button>

        <div
          className="transition-all duration-300 ease-in-out"
          style={{
            width: showNodeDetail ? "320px" : "0px",
            opacity: showNodeDetail ? 1 : 0,
            overflow: "hidden",
          }}
        >
          <NodeDetail node={selectedNode} />
        </div>
      </div>

      {/* Blast Radius overlay */}
      <BlastRadius
        node={selectedNodeId}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  );
}