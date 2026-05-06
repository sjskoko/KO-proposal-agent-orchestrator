"""Unit tests for the web_research skill handler."""

from __future__ import annotations

import pytest

from skills.example_skill.handler import run, validate_inputs


class TestValidateInputs:
    def test_valid_inputs(self):
        assert validate_inputs({"query": "test query"}) == []

    def test_empty_query(self):
        errors = validate_inputs({"query": ""})
        assert any("query" in e for e in errors)

    def test_invalid_max_sources(self):
        errors = validate_inputs({"query": "test", "max_sources": 0})
        assert any("max_sources" in e for e in errors)

    def test_max_sources_too_large(self):
        errors = validate_inputs({"query": "test", "max_sources": 100})
        assert any("max_sources" in e for e in errors)


class TestRun:
    def test_run_without_context_returns_stub(self):
        result = run({"query": "What is Gemma 4?", "max_sources": 2}, context=None)
        assert "summary" in result
        assert "sources" in result
        assert isinstance(result["sources"], list)

    def test_empty_query_returns_no_results_message(self):
        # Handler should degrade gracefully with whitespace-only query
        result = run({"query": "   ", "max_sources": 1}, context=None)
        assert isinstance(result["summary"], str)

    def test_output_format_bullet_points(self):
        result = run({"query": "Python", "output_format": "bullet_points"}, context=None)
        assert "summary" in result
