"""Learning-oriented MCP + LangGraph agent example.

What this version demonstrates (next-step topics):
1) Environment-driven configuration
2) Consistent message schema for agent input
3) Timeout + retry around tool/model invocation
4) Basic model fallback (OpenAI -> Watsonx)
5) Cleaner CLI loop with explicit error handling
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from langchain_ibm import ChatWatsonx
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5-nano")
    watsonx_model_id: str = os.getenv("WATSONX_MODEL_ID", "ibm/granite-3-3-8b-instruct")
    watsonx_url: str = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    watsonx_project_id: str = os.getenv("WATSONX_PROJECT_ID", "skills-network")
    thread_id: str = os.getenv("AGENT_THREAD_ID", "conversation_id")
    request_timeout_s: float = float(os.getenv("AGENT_TIMEOUT_SECONDS", "25"))
    max_retries: int = int(os.getenv("AGENT_MAX_RETRIES", "2"))


class AgentRunner:
    """Encapsulates agent setup + robust invocation logic."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = {"configurable": {"thread_id": settings.thread_id}}
        self.client = MultiServerMCPClient(
            {
                "context7": {
                    "url": "https://mcp.context7.com/mcp",
                    "transport": "streamable_http",
                },
                "met-museum": {
                    "command": "npx",
                    "args": ["-y", "metmuseum-mcp"],
                    "transport": "stdio",
                },
            }
        )

    async def _build_agents(self) -> tuple[Any, Any]:
        """Build two agents to enable simple fallback routing."""
        tools = await self.client.get_tools()
        checkpointer = InMemorySaver()

        openai_model = ChatOpenAI(model=self.settings.openai_model)
        watsonx_model = ChatWatsonx(
            model_id=self.settings.watsonx_model_id,
            url=self.settings.watsonx_url,
            project_id=self.settings.watsonx_project_id,
        )

        openai_agent = create_react_agent(
            model=openai_model,
            tools=tools,
            checkpointer=checkpointer,
        )
        watsonx_agent = create_react_agent(
            model=watsonx_model,
            tools=tools,
            checkpointer=checkpointer,
        )
        return openai_agent, watsonx_agent

    async def invoke_with_retry(self, agent: Any, user_text: str, *, system_prompt: str | None = None) -> str:
        """Invoke an agent with timeout + retries. Always use message-list schema."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_text})

        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    agent.ainvoke({"messages": messages}, config=self.config),
                    timeout=self.settings.request_timeout_s,
                )
                return response["messages"][-1].content
            except Exception as exc:  # noqa: BLE001 - tutorial-style broad catch for resilience
                last_error = exc
                if attempt >= self.settings.max_retries:
                    break
                backoff = 0.8 * (2**attempt)
                await asyncio.sleep(backoff)

        raise RuntimeError(f"Agent call failed after retries: {last_error}") from last_error


async def main() -> None:
    settings = Settings()
    runner = AgentRunner(settings)
    openai_agent, watsonx_agent = await runner._build_agents()

    system_prompt = (
        "You are a smart, useful agent with tools to access code library "
        "documentation and the Met Museum collection."
    )

    print("=== Agent Boot Test ===")
    intro = await runner.invoke_with_retry(
        openai_agent,
        "Give a brief introduction of what you do and the tools you can access.",
        system_prompt=system_prompt,
    )
    print(intro)

    while True:
        choice = input("\nMenu:\n1. Ask the agent a question\n2. Quit\nEnter your choice (1 or 2): ")

        if choice == "2":
            print("Goodbye!")
            break
        if choice != "1":
            print("Please type 1 or 2.")
            continue

        query = input("Your question\n> ").strip()
        if not query:
            print("Empty question. Please try again.")
            continue

        try:
            answer = await runner.invoke_with_retry(openai_agent, query)
        except Exception as openai_error:  # noqa: BLE001
            print(f"OpenAI path failed, falling back to Watsonx: {openai_error}")
            answer = await runner.invoke_with_retry(watsonx_agent, query)

        print(answer)


if __name__ == "__main__":
    asyncio.run(main())
