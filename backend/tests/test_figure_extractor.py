from backend.app.services.figure_extractor import find_captions


def test_find_figure_and_table_captions():
    text = """
    Figure 1: Overview of the proposed framework.
    Normal paragraph text.
    Table 2. Results on the benchmark datasets.
    Fig. 3 shows the ablation study.
    """

    captions = find_captions(text)

    assert captions == [
        "Figure 1: Overview of the proposed framework.",
        "Table 2. Results on the benchmark datasets.",
        "Fig. 3 shows the ablation study.",
    ]
