import { useState, useEffect } from "react";
import axios from "axios";

interface BlastRadiusData {
  node: string;
  reachable: {
    [key: string]: string[];
  };
}

const hopColors = {
  "1hop": "#C0392B",
  "2hop": "#E07B39",
  "3hop": "#C9A84C",
};

export function BlastRadius({
  node,
  onClose,
}: {
  node: string | null;
  onClose: () => void;
}) {
  const [blastRadius, setBlastRadius] = useState<BlastRadiusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!node) {
      setBlastRadius(null);
      return;
    }

    const fetchBlastRadius = async () => {
      try {
        setLoading(true);
        const response = await axios.post(
          `http://localhost:8000/blast-radius/${node}`
        );
        setBlastRadius(response.data);
        setError(null);
      } catch (err) {
        setError("Failed to compute blast radius");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchBlastRadius();
  }, [node]);

  if (!blastRadius) return null;

  const totalReachable = Object.values(blastRadius.reachable).reduce(
    (sum, nodes) => sum + nodes.length,
    0
  );

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-96 bg-[#141414] border border-[#2A2A2A] rounded-lg shadow-lg overflow-hidden flex flex-col z-20">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-[#2A2A2A] bg-[#0D0D0D]">
        <div>
          <div
            className="text-[11px] uppercase tracking-widest"
            style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
          >
            Blast Radius
          </div>
          <div
            className="text-[14px] font-bold"
            style={{ fontFamily: "Inter", color: "#D4A853" }}
          >
            {node}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-[#6B6B6B] hover:text-[#E8E8E8] px-2 py-1 hover:bg-[#2A2A2A] rounded transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading ? (
          <div
            className="text-[12px]"
            style={{ fontFamily: "JetBrains Mono", color: "#6B6B6B" }}
          >
            Computing reachability...
          </div>
        ) : error ? (
          <div
            className="text-[12px]"
            style={{ fontFamily: "JetBrains Mono", color: "#C0392B" }}
          >
            {error}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-[#0D0D0D] rounded p-2 text-center border border-[#2A2A2A]">
                <div
                  className="text-[11px]"
                  style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
                >
                  Total Reachable
                </div>
                <div
                  className="text-[18px] font-bold"
                  style={{ fontFamily: "JetBrains Mono", color: "#D4A853" }}
                >
                  {totalReachable}
                </div>
              </div>
              <div className="bg-[#0D0D0D] rounded p-2 text-center border border-[#2A2A2A]">
                <div
                  className="text-[11px]"
                  style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
                >
                  1-hop
                </div>
                <div
                  className="text-[18px] font-bold"
                  style={{ fontFamily: "JetBrains Mono", color: hopColors["1hop"] }}
                >
                  {blastRadius.reachable["1hop"]?.length || 0}
                </div>
              </div>
              <div className="bg-[#0D0D0D] rounded p-2 text-center border border-[#2A2A2A]">
                <div
                  className="text-[11px]"
                  style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
                >
                  2-hop
                </div>
                <div
                  className="text-[18px] font-bold"
                  style={{ fontFamily: "JetBrains Mono", color: hopColors["2hop"] }}
                >
                  {blastRadius.reachable["2hop"]?.length || 0}
                </div>
              </div>
            </div>

            {/* Hop details */}
            {Object.entries(blastRadius.reachable).map(([hop, nodes]) => (
              <div key={hop}>
                <div
                  className="text-[11px] font-bold mb-1 px-2 py-1 rounded"
                  style={{
                    fontFamily: "IBM Plex Mono",
                    color: "white",
                    backgroundColor: hopColors[hop as keyof typeof hopColors],
                  }}
                >
                  {hop.replace("hop", " Hops")}
                </div>
                {nodes.length === 0 ? (
                  <div
                    className="text-[11px] text-gray-500 px-2"
                    style={{ fontFamily: "JetBrains Mono" }}
                  >
                    — None
                  </div>
                ) : (
                  <div
                    className="text-[10px] space-y-0.5 px-2"
                    style={{ fontFamily: "JetBrains Mono", color: "#E8E8E8" }}
                  >
                    {nodes.map((n, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-1 truncate"
                        title={n}
                      >
                        <span style={{ color: "#6B6B6B" }}>→</span>
                        <span className="truncate">{n}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>

      {/* Footer */}
      <div
        className="text-[9px] px-3 py-2 border-t border-[#2A2A2A] bg-[#0D0D0D]"
        style={{ fontFamily: "JetBrains Mono", color: "#6B6B6B" }}
      >
        Assuming {node} is compromised, the above nodes are reachable within 3
        hops.
      </div>
    </div>
  );
}
