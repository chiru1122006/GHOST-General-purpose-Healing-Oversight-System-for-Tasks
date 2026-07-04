import pytest
from core.trajectory import TrajectoryTracker

def test_jaccard_identical():
    t = TrajectoryTracker()
    # Seed a trajectory first
    t.add_successful_trajectory("test_type", ["a", "b", "c", "d"])
    score = t.compute_adherence("test_type", ["a", "b", "c", "d"])
    assert score > 0.8, f"Expected > 0.8, got {score}"

def test_jaccard_disjoint():
    t = TrajectoryTracker()
    score = t.compute_adherence("web_research", ["fly_plane", "cook_food", "ride_horse"])
    assert score < 0.4, f"Expected < 0.4, got {score}"

def test_repetition_loop_detected():
    t = TrajectoryTracker()
    score = t.compute_adherence("web_research",
        ["search_web", "search_web", "search_web", "search_web"])
    assert score < 0.2, f"Repetition loop should score very low, got {score}"

def test_neutral_score_no_baseline():
    t = TrajectoryTracker()
    score = t.compute_adherence("nonexistent_task_type_xyz", ["do_thing"])
    assert score == 0.7, f"Should return neutral 0.7 with no baseline, got {score}"
