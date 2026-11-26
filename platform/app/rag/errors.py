class RagError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class RagDependencyError(RagError):
    def __init__(self) -> None:
        super().__init__(
            503, "dependency_unavailable", "A RAG dependency is unavailable."
        )


class RagNotReady(RagError):
    def __init__(self) -> None:
        super().__init__(503, "rag_not_ready", "RAG services are not ready.")


class RagParserError(RagError):
    def __init__(self) -> None:
        super().__init__(
            502, "parser_upstream_error", "The PDF parser returned an invalid response."
        )


class RagUnprocessablePdf(RagError):
    def __init__(self) -> None:
        super().__init__(
            422,
            "unprocessable_pdf",
            "The PDF could not be processed or contains no extractable text.",
        )
