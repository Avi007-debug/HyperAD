from typing import List, Any
from langchain_community.chat_models import ChatOllama
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.schema import SystemMessage

# Mock implementations for tools
def query_graph(query: str) -> str:
    """Mock query to the Graph Engine."""
    return f"Graph results for query: {query}. Node A connected to Node B."

def get_paths(source: str, target: str) -> str:
    """Mock path retrieval from Graph Engine."""
    return f"Path from {source} to {target}: {source} -> Group1 -> {target}"

def blast_radius(node: str) -> str:
    """Mock blast radius calculation."""
    return f"Blast radius for {node}: High. Compromises 15 other critical nodes."

def get_findings() -> str:
    """Mock retrieval of security findings."""
    return "Findings: 3 Kerberoasting accounts, 2 DCSync vulnerabilities."

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
