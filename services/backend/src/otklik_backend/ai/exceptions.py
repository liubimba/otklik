from otklik_backend.exceptions import ServerError


class GenerationCoverLetterError(ServerError):
    status_code = 500

    def __init__(self, detail: str | None = None):
        super().__init__(detail)


class AILayerUnhealthyError(ServerError):
    status_code = 409
    code = "AI_UNHEALTHY"
    detail = "ai layer unhealthy"
