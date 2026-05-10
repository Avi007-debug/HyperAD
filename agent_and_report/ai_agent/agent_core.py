from typing import List, Any
from langchain_community.chat_models import ChatOllama
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.schema import SystemMessage

import json
from algorithm.temporal_bellman_ford import run_temporal_bellman_ford, summarise_paths
from algorithm.tarjan_scc import run_tarjan_scc, enrich_scc_findings
from algorithm.hits_scorer import run_hits, hits_to_priority_list
from algorithm.blast_radius import run_blast_radius
from algorithm.graph_factory import make_tiny_graph

# Initialize a static graph for agent testing
AD_GRAPH, AD_ANSWERS = make_tiny_graph()
DA_NODES = AD_ANSWERS["da_nodes"]

def query_graph(query: str) -> str:
    """Query the AD graph for basic node info."""
    nodes = list(AD_GRAPH.nodes(data=True))
    results = [n for n in nodes if query.lower() in str(n[0]).lower()]
    return json.dumps([{"node": n[0], "attributes": n[1]} for n in results][:5])

def get_paths(source: str, target: str) -> str:
    """Retrieve shortest paths using Temporal Bellman-Ford."""
    targets = {target} if target and target.strip() else DA_NODES
    paths = run_temporal_bellman_ford(AD_GRAPH, da_nodes=targets)
    if source and source.strip():
        paths = [p for p in paths if p.source.lower() == source.lower()]
    if not paths:
        return "No paths found."
    return json.dumps([p.to_dict() for p in paths], indent=2)

def blast_radius(node: str) -> str:
    """Calculate blast radius from a compromised node."""
    res = run_blast_radius(AD_GRAPH, node.strip(), da_nodes=DA_NODES)
    return json.dumps(res.to_dict(), indent=2)

def get_findings() -> str:
    """Retrieve combined security findings."""
    paths = run_temporal_bellman_ford(AD_GRAPH, da_nodes=DA_NODES)
    bf_summary = summarise_paths(paths)
    
    sccs = run_tarjan_scc(AD_GRAPH)
    enriched_sccs = enrich_scc_findings(sccs, AD_GRAPH)
    
    hits, _ = run_hits(AD_GRAPH, top_n=5)
    hits_priority = hits_to_priority_list(hits)
    
    report = {
        "bellman_ford_summary": bf_summary,
        "scc_findings": enriched_sccs,
        "hits_priority": hits_priority
    }
    return json.dumps(report, indent=2)

# Define LangChain Tools
tools: List[Tool] = [
    Tool(
        name="query_graph",
        func=query_graph,
        description="Useful for querying the Active Directory graph database to find nodes and relationships."
    ),
    Tool(
        name="get_paths",
        func=lambda x: get_paths(*x.split(',')) if ',' in x else "Please provide source and target separated by comma.",
        description="Useful for finding attack paths between a source node and a target node. Input should be 'source,target'."
    ),
    Tool(
        name="blast_radius",
        func=blast_radius,
        description="Useful for determining the potential impact or blast radius if a specific node is compromised."
    ),
    Tool(
        name="get_findings",
        func=lambda _: get_findings(),
        description="Useful for retrieving the current list of known AD vulnerabilities and findings."
    )
]

def create_ad_security_agent() -> Any:
    """
    Creates and returns a LangChain ReAct agent configured as an AD Security Specialist.
    """
    # Initialize the LLM (Llama 3 8B via ChatOllama)
    llm = ChatOllama(model="llama3", temperature=0)

    # System prompt for the AD Security Specialist
    system_prompt = (
        "You are an elite Active Directory Security Specialist. Your primary objective is to "
        "analyze AD environments, identify attack paths, and evaluate the risk of potential compromises. "
        "Use your tools to query graph data, analyze blast radius, and report findings accurately. "
        "Think step-by-step to unravel complex multi-step attack paths."
    )

    agent_kwargs = {
        "system_message": SystemMessage(content=system_prompt)
    }

    # Initialize the ReAct agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        agent_kwargs=agent_kwargs,
        handle_parsing_errors=True
    )
    
    return agent

if __name__ == "__main__":
    # Example usage (Mock)
    agent = create_ad_security_agent()
    # response = agent.run("What is the blast radius of User_Admin?")
    # print(response)
