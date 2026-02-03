import asyncio
from agent.agent import Agent

async def main():
    agent = Agent(goal="API healthy")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
