interface NodeDetailProps {
  node: {
    id: string;
    label: string;
    type: "user" | "group" | "computer" | "service";
    authorityScore: number;
  } | null;
}

const typeLabels = {
  user: "User Account",
  group: "Security Group",
  computer: "Computer Object",
  service: "Service Account"
};

export function NodeDetail({ node }: NodeDetailProps) {
  if (!node) {
    return (
      <div className="w-[320px] h-full border-l border-[#1F1F1F] bg-[#141414] flex items-center justify-center">
        <div
          className="text-[13px]"
          style={{ fontFamily: "Inter", color: "#6B6B6B" }}
        >
          Select a node to view details
        </div>
      </div>
    );
  }

  const riskScore = Math.floor(node.authorityScore * 10);
  const getSeverityColor = (score: number) => {
    if (score >= 8) return "#C0392B";
    if (score >= 6) return "#E07B39";
    if (score >= 4) return "#C9A84C";
    return "#4A7C59";
  };

  return (
    <div className="w-[320px] h-full border-l border-[#1F1F1F] bg-[#141414] flex flex-col overflow-y-auto">
      <div className="p-4 border-b border-[#1F1F1F]">
        <div
          className="text-[14px] mb-1"
          style={{ fontFamily: "IBM Plex Mono", color: "#E8E8E8" }}
        >
          {node.label}
        </div>
        <div
          className="text-[11px]"
          style={{ fontFamily: "Inter", color: "#6B6B6B" }}
        >
          {typeLabels[node.type]}
        </div>
      </div>

      <div className="p-4 border-b border-[#1F1F1F]">
        <div
          className="text-[11px] mb-2"
          style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
        >
          PATHS TO DOMAIN ADMIN
        </div>
        <div
          className="text-[13px] mb-2"
          style={{ fontFamily: "Inter", color: "#E8E8E8" }}
        >
          2 paths found
        </div>
        <div
          className="text-[11px] space-y-1"
          style={{ fontFamily: "JetBrains Mono", color: "#6B6B6B" }}
        >
          <div>1-hop: {node.label} → DOMAIN_ADMINS</div>
          <div>2-hop: {node.label} → IT_ADMINS → DOMAIN_ADMINS</div>
        </div>
      </div>

      <div className="p-4 border-b border-[#1F1F1F]">
        <div
          className="text-[11px] mb-2"
          style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
        >
          BLAST RADIUS
        </div>
        <div
          className="space-y-1 text-[13px]"
          style={{ fontFamily: "Inter", color: "#E8E8E8" }}
        >
          <div className="flex justify-between">
            <span style={{ color: "#6B6B6B" }}>1-hop:</span>
            <span>4 nodes</span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: "#6B6B6B" }}>2-hop:</span>
            <span>12 nodes</span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: "#6B6B6B" }}>3+:</span>
            <span>31 nodes</span>
          </div>
        </div>
      </div>

      <div className="p-4 border-b border-[#1F1F1F]">
        <div
          className="text-[11px] mb-2"
          style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
        >
          RISK SCORE
        </div>
        <div
          className="text-[32px]"
          style={{
            fontFamily: "JetBrains Mono",
            color: getSeverityColor(riskScore)
          }}
        >
          {riskScore}
        </div>
      </div>

      <div className="p-4">
        <button
          className="text-[13px] transition-colors hover:text-[#E8E8E8]"
          style={{ fontFamily: "Inter", color: "#6B6B6B" }}
        >
          What if fixed?
        </button>
      </div>
    </div>
  );
}
