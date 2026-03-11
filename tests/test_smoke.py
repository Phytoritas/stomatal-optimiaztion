from stomatal_optimiaztion.domains.thorp import model_card_document_names


def test_smoke() -> None:
    assert len(model_card_document_names()) == 11
