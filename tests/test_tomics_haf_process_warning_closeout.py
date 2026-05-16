from pathlib import Path


def test_goal4a_process_warning_closeout_documents_non_blocking_warnings():
    text = Path("docs/architecture/tomics/goal3c_process_warnings_closeout.md").read_text(encoding="utf-8")

    assert "RAH SessionStart/Stop hooks" in text
    assert "operational convenience warning" in text
    assert "Closes #314" in text
    assert "Project attachment failed" in text
    assert "non-blocking" in text
    assert "not a code blocker" in text
