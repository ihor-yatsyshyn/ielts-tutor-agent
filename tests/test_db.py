import pytest

from db import repo
from errors import AppError


def test_student_roundtrip_and_update(student):
    assert student["test_type"] == "Academic"
    st = repo.update_student(student["id"], {"target_band": 6.5, "test_type": "General Training"})
    assert st["target_band"] == 6.5 and st["version"] == 2


def test_forbidden_field_rejected(student):
    with pytest.raises(AppError):
        repo.update_student(student["id"], {"id": "hack"})


def test_exercise_ownership(student, student2):
    ex = repo.create_exercise(student["id"], "writing",
                              {"exercise_type": "task2", "content": {"a": 1}}, "Academic")
    assert repo.get_exercise(student["id"], ex["id"]) is not None
    assert repo.get_exercise(student2["id"], ex["id"]) is None  # чужий студент


def test_attempt_idempotent(student):
    ex = repo.create_exercise(student["id"], "reading", {"exercise_type": "r", "content": {}}, "Academic")
    a1 = repo.save_attempt(student["id"], ex["id"], "reading", "sub-1", {}, {}, "verified_deterministic", 3, 4)
    a2 = repo.save_attempt(student["id"], ex["id"], "reading", "sub-1", {}, {}, "verified_deterministic", 4, 4)
    assert a1["id"] == a2["id"] and a2["duplicate"] is True


def test_plan_versions_keep_history(student):
    p1 = repo.create_plan(student["id"], "Academic", 7.0, 14, "r", [])
    p2 = repo.create_plan(student["id"], "Academic", 7.0, 14, "r2", [])
    assert (p1["version"], p2["version"]) == (1, 2)
    assert repo.get_active_plan(student["id"])["version"] == 2


def test_mistake_recurrence(student):
    repo.add_mistake(student["id"], None, "writing", "grammar", "He go", "He goes", "s-v agreement")
    m = repo.add_mistake(student["id"], None, "writing", "grammar", "he go", "He goes", "s-v agreement")
    assert m["recurrence_count"] == 2 and m["status"] == "recurring"
