import json

from scripts.rag_quality_eval import (
    DATASET_PATH,
    grade_results,
    render_pdf,
    validate_dataset,
)


def test_held_out_dataset_has_expected_size_and_balance() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    validate_dataset(dataset)

    assert len(dataset["documents"]) == 6
    assert sum(question["answerable"] for question in dataset["questions"]) == 20
    assert sum(not question["answerable"] for question in dataset["questions"]) == 10


def test_synthetic_pdf_writer_emits_a_two_page_pdf() -> None:
    pdf = render_pdf(["First page fact.", "Second page fact."])

    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.count(b"/Type /Page ") == 2
    assert pdf.endswith(b"%%EOF\n")


def test_grade_results_applies_agreed_acceptance_thresholds(tmp_path) -> None:
    results = []
    for index in range(20):
        results.append(
            {
                "id": f"A{index + 1:02}",
                "answerable": True,
                "grading": {
                    "answer_correct": index < 18,
                    "grounded": index < 18,
                    "citation_correct": True,
                    "abstained": None,
                },
            }
        )
    for index in range(10):
        results.append(
            {
                "id": f"U{index + 1:02}",
                "answerable": False,
                "grading": {
                    "answer_correct": None,
                    "grounded": True,
                    "citation_correct": True,
                    "abstained": True,
                },
            }
        )
    output = tmp_path / "graded-results.json"
    output.write_text(json.dumps({"results": results}), encoding="utf-8")

    assert grade_results(output) is True

    results[0]["grading"]["citation_correct"] = False
    output.write_text(json.dumps({"results": results}), encoding="utf-8")
    assert grade_results(output) is False
