from fastapi import APIRouter

from otklik_backend.api.dependencies import SessionDep
from otklik_backend.api.schemas import BoardPromptAPISchema, BoardPromptsAPISchema
from otklik_backend.core.board import Board
from otklik_backend.core.board_prompt import BoardPrompt
from otklik_backend.db.models import SettingsORM
from otklik_backend.db.repositories.settings import SettingsRepository

board_prompts_router: APIRouter = APIRouter(
    prefix="/board-prompts", tags=["board-prompts"]
)


def _to_schema(settings: SettingsORM) -> BoardPromptsAPISchema:
    prompts: dict[Board, BoardPromptAPISchema] = {}
    for key, raw in (settings.board_prompts or {}).items():
        parsed = BoardPrompt.from_stored(raw)
        if parsed is None:
            continue
        try:
            board = Board(key)
        except ValueError:
            continue
        prompts[board] = BoardPromptAPISchema(mode=parsed.mode, text=parsed.text)
    return BoardPromptsAPISchema(prompts=prompts)


@board_prompts_router.get("")
async def get_board_prompts_api(session: SessionDep) -> BoardPromptsAPISchema:
    settings = await SettingsRepository.get(session=session)
    return _to_schema(settings)


@board_prompts_router.put("/{board}")
async def set_board_prompt_api(
    board: Board, body: BoardPromptAPISchema, session: SessionDep
) -> BoardPromptsAPISchema:
    prompt = BoardPrompt.from_stored({"mode": body.mode.value, "text": body.text})
    entry = prompt.to_stored() if prompt is not None else None
    settings = await SettingsRepository.set_board_prompt(
        session=session, board_value=board.value, entry=entry
    )
    return _to_schema(settings)
