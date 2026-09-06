import pytest

from backend.agents.campaign import AgentRequest, BrandContext, MockCampaignAgentRunner, OutputGuardrailError
from genai.pydantic_compat import model_to_json


def test_mock_agent_returns_structured_campaign_draft_without_banned_terms():
    runner = MockCampaignAgentRunner()
    result = runner.run(
        AgentRequest(
            campaign_name="Autumn launch",
            brief="Launch a practical campaign planning workspace for small teams.",
            brand=BrandContext(voice="Clear and useful", banned_terms=["guaranteed"]),
        )
    )

    assert result.strategy.summary
    assert len(result.copy_draft.headlines) >= 2
    assert result.creative.image_prompts
    assert "guaranteed" not in model_to_json(result).lower()


def test_output_guardrail_blocks_banned_brand_terms():
    runner = MockCampaignAgentRunner(force_phrase="Guaranteed results")

    with pytest.raises(OutputGuardrailError, match="banned term"):
        runner.run(
            AgentRequest(
                campaign_name="Autumn launch",
                brief="Launch a practical campaign planning workspace for small teams.",
                brand=BrandContext(banned_terms=["guaranteed"]),
            )
        )
