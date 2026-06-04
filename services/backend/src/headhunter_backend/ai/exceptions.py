class GenerationCoverLetterException(Exception):
    def __init__(self, reason: str | None = None) -> None:
        super().__init__(reason)
