import textwrap

from digest.config import load_config
from digest.models import SeriesDef


def test_load_config_reads_toml_and_env(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        textwrap.dedent("""
        model = "claude-haiku-4-5"
        threshold = 0.4
        calibration = false
        suppress_days = 3
        escalation_factor = 1.5
        db_path = "state.db"
        timezone = "America/New_York"
        max_stories = 8

        [weights]
        social = 0.5
        breadth = 0.35
        spike = 0.15

        [ses]
        sender = "d@example.com"
        recipient = "you@example.com"
        aws_region = "us-east-1"

        [[rss_feeds]]
        url = "https://example.com/feed"
        series = "indycar"

        [[subreddits]]
        name = "formula1"
        series = "f1"

        [keywords]
        series_f1 = ["F1"]
        series_indycar = ["IndyCar"]
        teams = ["Ferrari"]
        drivers = ["Verstappen"]
        anchors = ["racing"]
    """)
    )
    monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "ua")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")

    cfg = load_config(str(cfg_file))

    assert cfg.model == "claude-haiku-4-5"
    assert cfg.calibration is False
    assert cfg.weights["breadth"] == 0.35
    assert cfg.escalation_factor == 1.5
    assert cfg.reddit_client_id == "cid"
    assert cfg.anthropic_api_key == "sk-ant"
    assert cfg.rss_feeds[0]["series"] == "indycar"
    assert cfg.subreddits[0]["name"] == "formula1"
    assert "Verstappen" in cfg.keywords["drivers"]


def test_load_config_reads_bluesky(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("bluesky_enabled = true\n")
    monkeypatch.setenv("BSKY_HANDLE", "andy.example.com")
    monkeypatch.setenv("BSKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")

    cfg = load_config(str(cfg_file))

    assert cfg.bluesky_enabled is True
    assert cfg.bsky_handle == "andy.example.com"
    assert cfg.bsky_app_password == "abcd-efgh-ijkl-mnop"


def test_load_config_defaults_when_calibration_true(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'calibration = true\n[ses]\nsender="a"\nrecipient="b"\naws_region="us-east-1"\n'
    )
    cfg = load_config(str(cfg_file))
    assert cfg.calibration is True
    assert cfg.model == "claude-haiku-4-5"  # default
    assert cfg.suppress_days == 3  # default


def test_load_config_parses_series_registry(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        textwrap.dedent("""
        max_stories = 15
        core_series = ["f1", "wec"]
        core_floor = 6

        [[series]]
        id = "f1"
        label = "Formula 1"
        terms = ["F1", "Grand Prix", "Verstappen"]

        [[series]]
        id = "wec"
        label = "WEC"
        terms = ["WEC", "Le Mans", "Hypercar"]
    """)
    )
    cfg = load_config(str(cfg_file))
    assert cfg.max_stories == 15
    assert cfg.core_series == ["f1", "wec"]
    assert cfg.core_floor == 6
    assert [s.id for s in cfg.series] == ["f1", "wec"]
    assert cfg.series[0] == SeriesDef(
        id="f1", label="Formula 1", terms=("F1", "Grand Prix", "Verstappen")
    )


def test_load_config_clamps_core_floor_to_max_stories(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        textwrap.dedent("""
        max_stories = 3
        core_floor = 10
        core_series = ["f1"]

        [[series]]
        id = "f1"
        label = "Formula 1"
        terms = ["F1"]
    """)
    )
    cfg = load_config(str(cfg_file))
    assert cfg.core_floor == 3  # clamped to max_stories


def test_load_config_rejects_unknown_core_series_id(tmp_path):
    import pytest

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        textwrap.dedent("""
        core_series = ["motogp"]

        [[series]]
        id = "f1"
        label = "Formula 1"
        terms = ["F1"]
    """)
    )
    with pytest.raises(ValueError, match="core_series"):
        load_config(str(cfg_file))
