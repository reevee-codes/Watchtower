import asyncio
from pathlib import Path

import yaml

from agent_async import Agent

_CONFIG_PATH = Path(__file__).parent / "config" / "endpoints.yaml"


async def main() -> None:
    config = yaml.safe_load(_CONFIG_PATH.read_text())
    agent = Agent(endpoints=config["endpoints"])
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
