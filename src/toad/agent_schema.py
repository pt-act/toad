from typing import TypedDict, Literal

type Tag = str
"""A tag used for categorizing the agent. For example: 'open-source', 'reasoning' """
type OS = Literal["macos", "linux", "windows", "*"]
"""An operating system identifier, or a '*" wildcard, if it is the same for all OSes."""
type Action = str
"""An action which the agent supports."""
type AgentType = Literal["coding", "chat"]
"""The type of agent."""
type AgentProtocol = Literal["acp"]
"""The protocol used to communicate with the agent"""


class Command(TypedDict):
    """Used to perform an action associate with an Agent."""

    description: str
    """Describes what the script will do. For example: 'Install Claude Code'."""
    command: str
    """Command to run."""


class Agent(TypedDict):
    """Describes an agent which Toad can connect to. Currently only Agent Client Protocol is supported."""

    identity: str
    """A unique identifier for this agent. Should be a domain the agent developer owns,
    although it doesn't have to resolve to anything.     
    For example: 'claude.anthropic.ai'"""
    name: str
    """The name of the agent. For example: 'Claude Code'."""
    short_name: str
    """A short name, usable on the command line. Try to make it unique. For example: 'claude'."""
    url: str
    """A URL for the agent."""
    protocol: AgentProtocol
    """The protocol used by the agent. Currently only 'acp' is supported."""
    type: "AgentType"
    """The type of the agent. Typically "coding" for agentic coding."""
    author_name: str
    """The author of the agent. For example 'Anthropic'."""
    author_url: str
    """The authors homepage. For example 'https://www.anthropic.com/'."""
    publisher_name: str
    """The publisher's name (an individual or organization that wrote this data)."""
    publisher_url: str
    """The publisher's url."""
    description: str
    """A description of the agent. A few sentences max."""
    tags: list[Tag]
    """Tags which identify the agent. Should be empty for now."""

    help: str
    """A Markdown document with additional details regarding the agent."""

    run_command: dict[OS, str]
    """Command to run the agent, by OS or wildcard."""

    actions: dict[OS, dict[Action, Command]]
    """Scripts to perform actions, typically at least to install the agent."""
