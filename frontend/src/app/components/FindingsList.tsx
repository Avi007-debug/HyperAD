import { useState, useEffect } from "react";
import axios from "axios";

interface Finding {
  id: string;
  title: string;
  mitreTactic: string;
  confidence: number;
  severity: "Critical" | "High" | "Medium" | "Low";
  evidence: string[];
  remediation: string;
}

const severityColors = {
  Critical: "#C0392B",
  High: "#E07B39",
  Medium: "#C9A84C",
  Low: "#4A7C59",
};

export function FindingsList({
  onFindingSelect,
}: {
  onFindingSelect: (finding: Finding) => void;
}) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"Risk Score ↓" | "Risk Score ↑">(
    "Risk Score ↓"
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch findings from API
  useEffect(() => {
    const fetchFindings = async () => {
      try {
        setLoading(true);
        const response = await axios.get("http://localhost:8000/findings");
        let sortedFindings = response.data.findings;

        // Sort by confidence
        if (sortOrder === "Risk Score ↓") {
          sortedFindings.sort((a: Finding, b: Finding) => b.confidence - a.confidence);
        } else {
          sortedFindings.sort((a: Finding, b: Finding) => a.confidence - b.confidence);
        }

        setFindings(sortedFindings);
        setError(null);
      } catch (err) {
        setError("Failed to load findings");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchFindings();
  }, [sortOrder]);

  if (loading) {
    return (
      <div className="w-[280px] h-full border-r border-[#1F1F1F] bg-[#141414] flex items-center justify-center text-[#6B6B6B] text-[12px]">
        Loading findings...
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-[280px] h-full border-r border-[#1F1F1F] bg-[#141414] flex items-center justify-center text-[#C0392B] text-[12px]">
        {error}
      </div>
    );
  }

  return (
    <div className="w-[280px] h-full border-r border-[#1F1F1F] bg-[#141414] flex flex-col">
      <div className="px-3 py-3 border-b border-[#1F1F1F]">
        <div
          className="text-[11px] tracking-[0.1em] mb-2"
          style={{ fontFamily: "IBM Plex Mono", color: "#6B6B6B" }}
        >
          FINDINGS ({findings.length})
        </div>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value as typeof sortOrder)}
          className="bg-transparent text-[#E8E8E8] text-[13px] border-none outline-none cursor-pointer"
          style={{ fontFamily: "Inter" }}
        >
          <option value="Risk Score ↓">Risk Score ↓</option>
          <option value="Risk Score ↑">Risk Score ↑</option>
        </select>
      </div>

      <div className="flex-1 overflow-y-auto">
        {findings.map((finding) => (
          <div
            key={finding.id}
            className="border-l-[3px] cursor-pointer hover:bg-[#1F1F1F] transition-colors"
            style={{ borderLeftColor: severityColors[finding.severity] }}
            onClick={() => {
              setExpandedId(expandedId === finding.id ? null : finding.id);
              onFindingSelect(finding);
            }}
          >
            <div className="py-2 px-3">
              <div className="flex items-start justify-between mb-1">
                <div
                  className="text-[12px] pr-2 flex-1"
                  style={{ fontFamily: "Inter", color: "#E8E8E8" }}
                >
                  {finding.title}
                </div>
                <div
                  className="text-[11px] whitespace-nowrap ml-2 px-1.5 py-0.5 bg-[#1F1F1F] rounded"
                  style={{ fontFamily: "JetBrains Mono", color: "#D4A853" }}
                >
                  {Math.round(finding.confidence * 100)}%
                </div>
              </div>
              <div className="flex items-center justify-between">
                <a
                  href={`https://attack.mitre.org/techniques/${finding.mitreTactic}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] hover:underline"
                  style={{
                    fontFamily: "JetBrains Mono",
                    color: "#7B68EE",
                  }}
                  onClick={(e) => e.stopPropagation()}
                >
                  {finding.mitreTactic}
                </a>
                <div
                  className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded"
                  style={{
                    fontFamily: "IBM Plex Mono",
                    color: "white",
                    backgroundColor: severityColors[finding.severity],
                  }}
                >
                  {finding.severity[0]}
                </div>
              </div>
            </div>

            {expandedId === finding.id && (
              <div
                className="px-3 py-2 bg-[#0D0D0D] text-[10px] border-t border-[#1F1F1F]"
                style={{ fontFamily: "JetBrains Mono", color: "#6B6B6B" }}
              >
                <div className="mb-2">
                  <div
                    className="text-[#D4A853] font-bold text-[11px] mb-1"
                    style={{ fontFamily: "IBM Plex Mono" }}
                  >
                    Evidence:
                  </div>
                  {finding.evidence.map((item, idx) => (
                    <div key={idx} className="mb-0.5">
                      • {item}
                    </div>
                  ))}
                </div>
                <div>
                  <div
                    className="text-[#D4A853] font-bold text-[11px] mb-1"
                    style={{ fontFamily: "IBM Plex Mono" }}
                  >
                    Remediation:
                  </div>
                  <div className="text-[#E8E8E8]">{finding.remediation}</div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
