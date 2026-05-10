import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import axios from "axios";

interface Node {
  id: string;
  label: string;
  type: "user" | "group" | "computer" | "service";
  authorityScore: number;
  isDomainAdmin?: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface Edge {
  source: string | Node;
  target: string | Node;
  weight: number;
}

interface BlastRadiusData {
  node: string;
  reachable: {
    [key: string]: string[];
  };
}

const nodeColors = {
  user: "#4A90D9",
  group: "#7B68EE",
  computer: "#888888",
  service: "#F5A623",
  da: "#C0392B",
};

export function GraphExplorer({
  onNodeSelect,
}: {
  onNodeSelect: (node: Node) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [blastRadius, setBlastRadius] = useState<BlastRadiusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const simRef = useRef<d3.Simulation<Node, Edge> | null>(null);

  // Fetch graph data from API
  useEffect(() => {
    const fetchGraph = async () => {
      try {
        setLoading(true);
        const response = await axios.get("http://localhost:8000/graph");
        const { nodes: rawNodes, edges: rawEdges } = response.data;
        setNodes(rawNodes);
        setEdges(rawEdges);
        setError(null);
      } catch (err) {
        setError("Failed to load graph data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, []);

  // D3 Force Simulation Setup
  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return;

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create force simulation
    const sim = d3
      .forceSimulation<Node>(nodes)
      .force(
        "link",
        d3
          .forceLink<Node, Edge>(edges)
          .id((d) => d.id)
          .distance(100)
          .strength((d) => 1 - d.weight / 10)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(40));

    simRef.current = sim;

    // Clear previous content
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current);

    // Add zoom behavior
    const g = svg.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Draw edges (lines)
    const edgesSelection = g
      .selectAll("line")
      .data(edges)
      .enter()
      .append("line")
      .attr("stroke", (d) => {
        const weight = d.weight;
        if (weight > 7) return "#C0392B";
        if (weight >= 4) return "#E07B39";
        return "#2A2A2A";
      })
      .attr("stroke-width", (d) => d.weight / 3)
      .attr("opacity", 0.6);

    // Draw nodes (circles)
    const nodesSelection = g
      .selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("r", (d) => 6 + d.authorityScore * 10)
      .attr("fill", (d) => {
        if (d.isDomainAdmin) return nodeColors.da;
        return nodeColors[d.type] || "#999";
      })
      .attr("stroke", "#1F1F1F")
      .attr("stroke-width", 2)
      .attr("cursor", "pointer")
      .on("click", (event, d) => {
        setSelectedNode(d.id);
        onNodeSelect(d);
        handleNodeClick(d);
      })
      .on("mouseover", function (event, d) {
        d3.select(this).attr("stroke-width", 3).attr("stroke", "#D4A853");
      })
      .on("mouseout", function (event, d) {
        if (selectedNode !== d.id) {
          d3.select(this).attr("stroke-width", 2).attr("stroke", "#1F1F1F");
        }
      });

    // Add labels
    const labels = g
      .selectAll("text")
      .data(nodes)
      .enter()
      .append("text")
      .attr("font-size", 11)
      .attr("font-family", "JetBrains Mono, monospace")
      .attr("text-anchor", "middle")
      .attr("dy", ".35em")
      .attr("fill", "#E8E8E8")
      .attr("pointer-events", "none")
      .text((d) => d.label)
      .attr("opacity", 0);

    // Update positions on each tick
    sim.on("tick", () => {
      edgesSelection
        .attr("x1", (d) => (d.source as Node).x || 0)
        .attr("y1", (d) => (d.source as Node).y || 0)
        .attr("x2", (d) => (d.target as Node).x || 0)
        .attr("y2", (d) => (d.target as Node).y || 0);

      nodesSelection.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);

      labels.attr("x", (d) => d.x || 0).attr("y", (d) => d.y || 0);
    });

    // Highlight blast radius
    if (blastRadius) {
      const hops = blastRadius.reachable;
      const colors = { "1hop": "#C0392B", "2hop": "#E07B39", "3hop": "#C9A84C" };

      nodesSelection.attr("stroke", (d) => {
        for (const [hop, nodeList] of Object.entries(hops)) {
          if (nodeList.includes(d.id)) {
            return colors[hop] || "#D4A853";
          }
        }
        return "#1F1F1F";
      });

      nodesSelection.attr("stroke-width", (d) => {
        for (const [_, nodeList] of Object.entries(hops)) {
          if (nodeList.includes(d.id)) {
            return 4;
          }
        }
        return selectedNode === d.id ? 3 : 2;
      });
    }

    // Show/hide labels on selection
    if (selectedNode) {
      labels.attr("opacity", (d) => (d.id === selectedNode ? 1 : 0));
    }

    return () => {
      sim.stop();
    };
  }, [nodes, edges, selectedNode, blastRadius, onNodeSelect]);

  const handleNodeClick = async (node: Node) => {
    try {
      const response = await axios.post(
        `http://localhost:8000/blast-radius/${node.id}`
      );
      setBlastRadius(response.data);
    } catch (err) {
      console.error("Failed to fetch blast radius:", err);
    }
  };

  const handleClearBlastRadius = () => {
    setBlastRadius(null);
    setSelectedNode(null);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#0D0D0D] text-[#6B6B6B]">
        Loading graph...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#0D0D0D] text-[#C0392B]">
        {error}
      </div>
    );
  }

  return (
    <div className="flex-1 relative bg-[#0D0D0D]">
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ background: "#0D0D0D" }}
      />

      {blastRadius && (
        <div className="absolute bottom-4 left-4 bg-[#1F1F1F] border border-[#2A2A2A] rounded p-3 text-[12px] max-w-xs">
          <div className="text-[#D4A853] font-bold mb-2">Blast Radius</div>
          <div className="space-y-1 text-[#E8E8E8]">
            {Object.entries(blastRadius.reachable).map(([hop, nodes]) => (
              <div key={hop}>
                <span className="text-[#6B6B6B]">{hop}:</span>{" "}
                {nodes.length === 0 ? "None" : nodes.join(", ")}
              </div>
            ))}
          </div>
          <button
            onClick={handleClearBlastRadius}
            className="mt-3 px-2 py-1 bg-[#2A2A2A] hover:bg-[#3A3A3A] rounded text-[#6B6B6B] hover:text-[#E8E8E8] transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-[#1F1F1F] border border-[#2A2A2A] rounded p-3 text-[11px]">
        <div className="text-[#D4A853] font-bold mb-2">Legend</div>
        <div className="space-y-1 text-[#6B6B6B]">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ background: nodeColors.user }}
            />
            <span>User</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ background: nodeColors.group }}
            />
            <span>Group</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ background: nodeColors.computer }}
            />
            <span>Computer</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ background: nodeColors.service }}
            />
            <span>Service</span>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ background: nodeColors.da }}
            />
            <span>Domain Admin</span>
          </div>
        </div>
      </div>
    </div>
  );
}
