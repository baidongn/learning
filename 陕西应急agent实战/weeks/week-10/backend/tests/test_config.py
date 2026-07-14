from highway_agent.config import Settings


def test_live_provider_defaults_to_current_deepseek_model() -> None:
    settings = Settings()

    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"

