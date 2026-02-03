from agent.agent import Agent
from agent.state import AgentState
from unittest.mock import AsyncMock
import pytest


@pytest.mark.asyncio
async def test_ok_count(mocker):
    mocker.patch("agent.agent.check_api", new=AsyncMock(return_value=("OK", 10.0)))
    agent = Agent(goal="whatever")
    await agent.run()
    assert agent.state.ok_count == 3

@pytest.mark.asyncio
async def test_healthy_stop(mocker):
    mocker.patch("agent.agent.check_api", new=AsyncMock(return_value=("ERROR", 123.0)))
    agent = Agent(goal="whatever")
    await agent.run()
    assert agent.last_decision == "STOP"