"""Skill eval for web_research — runs handler against fixture inputs."""

from skills.example_skill.handler import run, validate_inputs


class TestWebResearchSkillEval:
    def test_validate_passes_for_good_input(self):
        errors = validate_inputs({"query": "Gemma 4 features", "max_sources": 3})
        assert errors == []

    def test_run_returns_expected_shape(self):
        result = run({"query": "test", "max_sources": 1}, context=None)
        assert "summary" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    def test_run_with_output_format_bullet_points(self):
        result = run({"query": "Python", "output_format": "bullet_points"}, context=None)
        assert isinstance(result["summary"], str)
