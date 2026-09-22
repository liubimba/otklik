from otklik_backend.api.schemas import (
    BoardPromptsAPISchema,
    SettingsAPISchema,
)


def test_board_prompts_start_empty(client):
    response = client.get("/api/v1/board-prompts")
    assert response.status_code == 200
    assert BoardPromptsAPISchema.model_validate(response.json()).prompts == {}


def test_board_prompt_roundtrips_per_board(client):
    put = client.put(
        "/api/v1/board-prompts/kwork",
        json={"mode": "replace", "text": "Отклик на проект"},
    )
    assert put.status_code == 200

    got = BoardPromptsAPISchema.model_validate(
        client.get("/api/v1/board-prompts").json()
    )
    kwork = got.prompts["kwork"]
    assert kwork.mode.value == "replace"
    assert kwork.text == "Отклик на проект"
    assert "hh_ru" not in got.prompts


def test_blank_text_removes_the_board_prompt(client):
    client.put(
        "/api/v1/board-prompts/habr",
        json={"mode": "append", "text": "Короче обычного"},
    )
    cleared = client.put(
        "/api/v1/board-prompts/habr",
        json={"mode": "append", "text": "   "},
    )
    assert cleared.status_code == 200
    got = BoardPromptsAPISchema.model_validate(
        client.get("/api/v1/board-prompts").json()
    )
    assert "habr" not in got.prompts


def test_saving_settings_preserves_board_prompts(client):
    client.put(
        "/api/v1/board-prompts/kwork",
        json={"mode": "replace", "text": "Отклик на проект"},
    )

    body = SettingsAPISchema.model_validate(
        client.get("/api/v1/settings").json()
    ).model_dump(mode="json")
    body["llm"]["letter_style"] = "casual"
    assert client.put("/api/v1/settings", json=body).status_code == 200

    got = BoardPromptsAPISchema.model_validate(
        client.get("/api/v1/board-prompts").json()
    )
    assert got.prompts["kwork"].text == "Отклик на проект"


def test_unknown_board_is_rejected(client):
    response = client.put(
        "/api/v1/board-prompts/telegram",
        json={"mode": "append", "text": "hi"},
    )
    assert response.status_code == 422
