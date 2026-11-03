"""
Tests for the fine-tuning data rules and the promotion gate. The training script
has its own smoke test, which only runs where torch and peft are installed.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FINETUNING_DIR = Path(__file__).resolve().parents[2] / "finetuning"
sys.path.insert(0, str(FINETUNING_DIR))

import agents  # noqa: E402
import build_dataset  # noqa: E402
import draft_examples  # noqa: E402
import evaluate_model  # noqa: E402
import launch_training  # noqa: E402
import promotion_gate  # noqa: E402


def example(number=1, level="conforming", control="A.7.1", source=None, **overrides):
    return {
        "id": f"ex-{number}",
        "control_id": control,
        "evidence": f"El perímetro físico número {number} cuenta con control de acceso verificado en sitio.",
        "conformity_level": level,
        "maturity_score": 3,
        "finding": "Hallazgo",
        "recommendation": "Recomendación",
        "source_document": source or f"reporte-{number % 37}.pdf",
        "review_status": "approved",
        "reviewed_by": "auditor@example.com",
        **overrides,
    }


def write_curated(path, rows):
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")


def balanced(count=200):
    levels = sorted(build_dataset.CONFORMITY_LEVELS)
    return [example(i, level=levels[i % len(levels)]) for i in range(count)]


class TestAgents:
    def test_covers_all_seven_agents_including_physical_controls(self):
        assert len(agents.AGENTS) == 7
        assert "controls_a7" in agents.AGENTS

    def test_annex_a_has_93_controls(self):
        assert len(agents.ANNEX_A_2022) == 93

    @pytest.mark.parametrize("agent", sorted(agents.AGENTS))
    def test_uses_production_system_prompt(self, agent):
        assert "ISO 27001" in agents.system_prompt(agent)


class TestValidation:
    def check(self, row, agent="controls_a7", holdout=frozenset()):
        build_dataset.validate_example(row, agent, holdout)

    def test_valid_example_passes(self):
        self.check(example())

    @pytest.mark.parametrize("status", ["pending_review", "rejected", ""])
    def test_unreviewed_examples_are_rejected(self, status):
        with pytest.raises(build_dataset.DatasetError):
            self.check(example(review_status=status))

    def test_reviewer_is_required(self):
        with pytest.raises(build_dataset.DatasetError):
            self.check(example(reviewed_by=" "))

    def test_invented_control_is_rejected(self):
        with pytest.raises(build_dataset.DatasetError):
            self.check(example(control="A.14.2.5"))

    def test_control_of_another_domain_is_rejected(self):
        with pytest.raises(build_dataset.DatasetError):
            self.check(example(control="A.5.1"))

    def test_unknown_label_is_rejected(self):
        with pytest.raises(build_dataset.DatasetError):
            self.check(example(level="observation"))

    @pytest.mark.parametrize("score", [6, -1, "3", 2.5])
    def test_invalid_maturity_is_rejected(self, score):
        with pytest.raises(build_dataset.DatasetError):
            self.check(example(maturity_score=score))

    def test_evaluation_set_overlap_is_rejected(self):
        row = example()
        holdout = {build_dataset.normalize_text(row["evidence"])}
        with pytest.raises(build_dataset.DatasetError, match="evaluation set"):
            self.check(row, holdout=holdout)

    def test_holdout_files_are_loaded(self):
        assert len(build_dataset.holdout_fingerprints()) >= 30


class TestBuild:
    def test_builds_chat_examples(self, tmp_path):
        curated = tmp_path / "controls_a7.jsonl"
        write_curated(curated, balanced())
        train, val = build_dataset.build_agent_dataset("controls_a7", curated, set())
        assert train and val
        roles = [m["role"] for m in train[0]["messages"]]
        assert roles == ["system", "user", "assistant"]
        answer = json.loads(train[0]["messages"][-1]["content"])
        assert answer["control_id"] == "A.7.1"

    def test_too_few_examples_are_rejected(self, tmp_path):
        curated = tmp_path / "controls_a7.jsonl"
        write_curated(curated, balanced(40))
        with pytest.raises(build_dataset.DatasetError):
            build_dataset.build_agent_dataset("controls_a7", curated, set())

    def test_missing_label_class_is_rejected(self, tmp_path):
        curated = tmp_path / "controls_a7.jsonl"
        write_curated(curated, [example(i) for i in range(200)])
        with pytest.raises(build_dataset.DatasetError, match="training examples of"):
            build_dataset.build_agent_dataset("controls_a7", curated, set())

    def test_duplicates_are_rejected(self, tmp_path):
        curated = tmp_path / "controls_a7.jsonl"
        write_curated(curated, [example(1), example(1)])
        with pytest.raises(build_dataset.DatasetError, match="duplicate"):
            build_dataset.build_agent_dataset("controls_a7", curated, set())

    def test_one_document_never_lands_on_both_sides(self, tmp_path):
        curated = tmp_path / "controls_a7.jsonl"
        write_curated(curated, balanced())
        train, val = build_dataset.build_agent_dataset("controls_a7", curated, set())
        by_id = {row["id"]: row["source_document"] for row in balanced()}
        assert not {by_id[r["id"]] for r in train} & {by_id[r["id"]] for r in val}

    def test_cli_fails_when_there_is_no_reviewed_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["build", "--out", str(tmp_path), "--curated-dir", str(tmp_path)])
        assert build_dataset.main() == 1


class TestDrafts:
    def answer(self, *findings):
        client = MagicMock()
        client.converse.return_value = {
            "output": {"message": {"content": [{"text": json.dumps({"findings": list(findings)})}]}}
        }
        return client

    def test_drafts_are_never_approved(self):
        passage = "El control de acceso no se revisa desde 2021."
        client = self.answer({"control_id": "A.5.18", "evidence": "no se revisa desde 2021", "conformity_level": "minor_nonconformity"})
        drafts = draft_examples.draft_from_passage(client, "m", passage, "r.pdf")
        assert drafts[0]["review_status"] == "pending_review"
        assert drafts[0]["reviewed_by"] == ""
        with pytest.raises(build_dataset.DatasetError):
            build_dataset.validate_example(drafts[0], "controls_a5", set())

    def test_quote_not_in_source_is_discarded(self):
        client = self.answer({"control_id": "A.5.18", "evidence": "cita inventada"})
        assert draft_examples.draft_from_passage(client, "m", "otro texto", "r.pdf") == []

    def test_invented_control_is_discarded(self):
        client = self.answer({"control_id": "A.99.1", "evidence": "texto"})
        assert draft_examples.draft_from_passage(client, "m", "texto", "r.pdf") == []

    def test_unparseable_answer_is_skipped(self):
        client = MagicMock()
        client.converse.return_value = {"output": {"message": {"content": [{"text": "lo siento"}]}}}
        assert draft_examples.draft_from_passage(client, "m", "texto", "r.pdf") == []


class TestGate:
    def holdout(self):
        return [
            {"control_id": f"A.5.{i}", "conformity_level": "conforming", "maturity_score": 3}
            for i in range(1, 21)
        ]

    def predictions(self, correct, total=20, maturity=3):
        return {
            f"A.5.{i}": {
                "conformity_level": "conforming" if i <= correct else "major_nonconformity",
                "maturity_score": maturity,
            }
            for i in range(1, total + 1)
        }

    def test_holdout_covers_every_domain_with_schema_labels(self):
        holdout = evaluate_model.load_holdout()
        assert len(holdout) == 30
        assert {item["agent"] for item in holdout} == {"controls_a5", "controls_a6", "controls_a7", "controls_a8"}
        assert {item["conformity_level"] for item in holdout} <= build_dataset.CONFORMITY_LEVELS

    def test_clear_improvement_is_promoted(self):
        holdout = self.holdout()
        baseline = promotion_gate.score(self.predictions(10), holdout)
        candidate = promotion_gate.score(self.predictions(15), holdout)
        assert promotion_gate.decide(baseline, candidate) == []

    def test_marginal_improvement_is_not_promoted(self):
        holdout = self.holdout()
        baseline = promotion_gate.score(self.predictions(10), holdout)
        candidate = promotion_gate.score(self.predictions(10), holdout)
        assert promotion_gate.decide(baseline, candidate)

    def test_worse_maturity_blocks_promotion(self):
        holdout = self.holdout()
        baseline = promotion_gate.score(self.predictions(10), holdout)
        candidate = promotion_gate.score(self.predictions(20, maturity=1), holdout)
        assert any("maturity" in reason for reason in promotion_gate.decide(baseline, candidate))

    def test_malformed_predictions_count_as_wrong(self):
        scored = promotion_gate.score({"A.5.1": None}, self.holdout())
        assert scored["valid_rate"] == 0
        assert scored["concordance"] == 0

    def test_invalid_output_blocks_promotion(self):
        holdout = self.holdout()
        baseline = promotion_gate.score(self.predictions(2), holdout)
        predictions = self.predictions(15, total=15)
        candidate = promotion_gate.score(predictions, holdout)
        assert any("valid_rate" in reason for reason in promotion_gate.decide(baseline, candidate))


class TestLaunch:
    def test_default_does_not_launch(self, monkeypatch, capsys):
        monkeypatch.setattr(launch_training, "launch", MagicMock(side_effect=AssertionError("launched")))
        monkeypatch.setattr(sys, "argv", ["launch", "--agent", "all", "--role-arn", "r", "--train-s3", "s3://b/d"])
        assert launch_training.main() == 0
        assert "Plan only" in capsys.readouterr().out

    def test_plan_points_each_agent_to_its_own_data(self):
        plan = launch_training.job_plan("controls_a7", "s3://b/d/")
        assert plan["train_uri"] == "s3://b/d/controls_a7/"
        assert plan["hyperparameters"]["model_id"] == agents.SUB_AGENT_BASE
