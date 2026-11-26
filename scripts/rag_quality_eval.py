"""Run and grade the held-out synthetic RAG quality evaluation."""

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

import httpx

DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "evaluation"
    / "rag-quality-dataset.json"
)
NO_SUPPORT_ANSWER = (
    "The indexed documents do not provide enough information to answer this question."
)


def render_pdf(pages: list[str]) -> bytes:
    if not pages:
        raise ValueError("A PDF must contain at least one page.")

    page_objects = [4 + 2 * index for index in range(len(pages))]
    page_kids = " ".join(f"{number} 0 R" for number in page_objects)
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{page_kids}] /Count {len(pages)} >>".encode("ascii"),
        (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
            b"/Encoding /WinAnsiEncoding >>"
        ),
    ]

    for index, page_text in enumerate(pages):
        page_number = page_objects[index]
        content_number = page_number + 1
        wrapped_lines = [
            line
            for paragraph in page_text.splitlines()
            for line in textwrap.wrap(paragraph, width=82) or [""]
        ]
        commands = ["BT /F1 11 Tf 15 TL 50 750 Td"]
        for line in wrapped_lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({escaped}) Tj T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> "
                    f"/Contents {content_number} 0 R >>"
                ).encode("ascii"),
                f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
                + stream
                + b"\nendstream",
            ]
        )

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


def validate_dataset(dataset: dict[str, Any]) -> None:
    documents = dataset.get("documents")
    questions = dataset.get("questions")
    if not isinstance(documents, list) or not 6 <= len(documents) <= 10:
        raise ValueError("The quality evaluation must include 6 to 10 PDFs.")
    if not isinstance(questions, list):
        raise ValueError("The quality evaluation has no question list.")
    answerable = sum(item.get("answerable") is True for item in questions)
    unanswerable = sum(item.get("answerable") is False for item in questions)
    if answerable != 20 or unanswerable != 10 or len(questions) != 30:
        raise ValueError(
            "The dataset must contain 20 answerable and 10 unanswerable questions."
        )


def run_evaluation(
    *,
    base_url: str,
    model: str,
    output: Path,
    timeout_seconds: float,
) -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    validate_dataset(dataset)
    output_items: list[dict[str, Any]] = []
    upload_results: list[dict[str, Any]] = []

    with httpx.Client(
        base_url=base_url.rstrip("/"),
        timeout=httpx.Timeout(timeout_seconds, connect=10.0),
        trust_env=False,
    ) as client:
        health = client.get("/health/rag")
        if health.status_code != 200 or health.json().get("status") != "ready":
            raise RuntimeError(
                f"RAG is not ready: HTTP {health.status_code} {health.text[:300]}"
            )

        for document in dataset["documents"]:
            pdf_bytes = render_pdf(document["pages"])
            response = client.post(
                "/api/v1/knowledge/documents",
                files={
                    "file": (
                        document["filename"],
                        pdf_bytes,
                        "application/pdf",
                    )
                },
            )
            if not response.is_success:
                raise RuntimeError(
                    f"Could not index {document['filename']}: "
                    f"HTTP {response.status_code} {response.text[:500]}"
                )
            upload_results.append(response.json())

        for question in dataset["questions"]:
            response = client.post(
                "/api/v1/rag/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": question["question"]}],
                    "options": {"temperature": 0},
                },
            )
            response_body: dict[str, Any]
            if response.is_success:
                response_body = response.json()
                answer = response_body.get("message", {}).get("content", "")
                sources = response_body.get("sources", [])
            else:
                answer = ""
                sources = []
                response_body = {"error": response.text[:1000]}
            output_items.append(
                {
                    **question,
                    "http_status": response.status_code,
                    "answer": answer,
                    "sources": sources,
                    "response_error": response_body.get("error"),
                    "grading": {
                        "answer_correct": None,
                        "grounded": None,
                        "citation_correct": None,
                        "abstained": None,
                    },
                }
            )

    result = {
        "dataset_version": dataset["dataset_version"],
        "base_url": base_url,
        "model": model,
        "uploads": upload_results,
        "grading_guide": {
            "answer_correct": "Answer addresses the expected answer accurately.",
            "grounded": (
                "Every factual claim is supported by the indexed PDFs; for "
                "unanswerable questions, no answer is invented."
            ),
            "citation_correct": (
                "For answerable questions, cited filename and page match the "
                "evidence. For unanswerable questions, no unsupported citation "
                "is present."
            ),
            "abstained": (
                "For an unanswerable question, the response clearly says the "
                "documents do not contain enough information."
            ),
        },
        "results": output_items,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(output_items)} responses to {output}")
    print("Review each result and fill in its four grading fields before grading.")


def grade_results(path: Path) -> bool:
    result = json.loads(path.read_text(encoding="utf-8"))
    items = result.get("results")
    if not isinstance(items, list) or len(items) != 30:
        raise ValueError("The result file must contain all 30 evaluation responses.")

    missing: list[str] = []
    answerable_passes = 0
    answerable_citations_correct = 0
    unanswerable_passes = 0
    for item in items:
        grading = item.get("grading") or {}
        required = (
            ("answer_correct", "grounded", "citation_correct")
            if item.get("answerable") is True
            else ("grounded", "citation_correct", "abstained")
        )
        if any(not isinstance(grading.get(field), bool) for field in required):
            missing.append(str(item.get("id", "unknown")))
            continue
        if item["answerable"] is True:
            if grading["answer_correct"] and grading["grounded"]:
                answerable_passes += 1
            if grading["citation_correct"]:
                answerable_citations_correct += 1
        elif (
            grading["abstained"] and grading["grounded"] and grading["citation_correct"]
        ):
            unanswerable_passes += 1

    print(f"Correct, grounded answerable responses: {answerable_passes}/20 (need 18)")
    print(f"Correct answerable citations: {answerable_citations_correct}/20 (need 20)")
    print(f"Safe unanswerable responses: {unanswerable_passes}/10 (need 10)")
    if missing:
        print(f"Missing manual grades: {', '.join(missing)}")
    passed = (
        not missing
        and answerable_passes >= 18
        and answerable_citations_correct == 20
        and unanswerable_passes == 10
    )
    print("Evaluation: PASS" if passed else "Evaluation: FAIL")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--output", type=Path, default=Path("rag-quality-results.json"))
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument(
        "--grade",
        type=Path,
        help="Grade a response file after completing its manual grading fields.",
    )
    args = parser.parse_args()
    if args.grade is not None:
        return 0 if grade_results(args.grade) else 1
    run_evaluation(
        base_url=args.base_url,
        model=args.model,
        output=args.output,
        timeout_seconds=args.timeout_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
