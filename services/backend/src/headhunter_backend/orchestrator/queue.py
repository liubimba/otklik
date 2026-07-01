# Back-compat shim: the runtime consumer is now
# orchestrator/workers/letter_sending.py::LetterSendingWorker.
# Import sites using the historical `Orchestrator` type continue to work,
# but new code should reference LetterSendingWorker directly. Removed once
# the last import migrates (stage 4.3+).
from headhunter_backend.orchestrator.workers.letter_sending import (
    LetterSendingWorker as Orchestrator,
)

__all__ = ["Orchestrator"]
