from pathlib import Path


DOCS = [
    Path("docs/manuscript/tomics_haf_2025_2c_methods_outline.md"),
    Path("docs/manuscript/tomics_haf_2025_2c_results_outline.md"),
    Path("docs/manuscript/tomics_haf_2025_2c_limitations_outline.md"),
    Path("docs/manuscript/tomics_haf_2025_2c_figures_table_plan.md"),
]


def test_goal4a_manuscript_outlines_include_claim_boundaries():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in DOCS)

    assert "DMC `0.056`" in combined or "DMC is fixed at `0.056`" in combined
    assert "estimated dry-yield basis" in combined
    assert "one compatible measured HAF dataset" in combined
    assert "not direct allocation validation" in combined
    assert "No shipped TOMICS default was changed" in combined
    assert "manifest-backed" in combined
    assert "universal multi-season generalization" in combined
