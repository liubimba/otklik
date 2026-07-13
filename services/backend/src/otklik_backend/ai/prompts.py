from collections.abc import Sequence

from otklik_backend.api.schemas import VacancyAPISchema, WorkFormat, EmploymentType
from litellm import (
    AllMessageValues,
    ChatCompletionAssistantMessage,
    ChatCompletionUserMessage,
    ChatCompletionSystemMessage,
    ChatCompletionTextObject,
)
from typing import List


class PromptBuilder:
    __default_system_prompt: str = (
        "Ты пишешь сопроводительные письма для откликов на вакансии.\n"
        "Правила:\n"
        "- Пиши письмо на языке вакансии. Для русской вакансии — только на естественном русском языке, без слов и символов других языков (никаких латинских или иероглифических вставок посреди текста).\n"
        "- Основывай каждый факт строго на резюме кандидата. Не приписывай ему опыт, навыки, должности, цифры или достижения, которых в резюме нет.\n"
        "- Если в резюме нет опыта, который требует вакансия, — не выдумывай его и не отказывайся писать письмо. Честно свяжи реальные и переносимые навыки кандидата с задачами вакансии.\n"
        "- Опирайся на конкретные детали из описания вакансии и связывай их с фактами из резюме.\n"
        "- Используй название должности, компании и другие поля вакансии как есть; никогда не заменяй их скобочными заглушками вида [Компания], [Должность], [Position].\n"
        "- Не подписывай письмо: не ставь в конце имя, подпись или заглушку вроде [Ваше имя], [Имя], [Your name]. Получатель уже видит, кто откликается. Заканчивай последним содержательным предложением.\n"
        "- Не начинай с обращения-заглушки; если имя адресата неизвестно, начинай прямо с сути.\n"
        "- Выводи только текст письма: без markdown, без строки «Тема:»/«Subject:», без пояснений до или после.\n"
        "- Держи письмо кратким (примерно до 250 слов), если вакансия явно не требует более длинного и формального формата."
    )

    def __init__(self) -> None:
        pass

    def build_cover_letter_prompt(
        self,
        vacancy_model: VacancyAPISchema,
        resume: str,
        style: str,
        system_prompt: str | None = None,
    ) -> List[AllMessageValues]:
        base_system: str = (
            system_prompt if system_prompt is not None else self.__default_system_prompt
        )
        if style.strip():
            base_system = f"{base_system}\n\nТон и стиль письма: {style.strip()}."

        user_text: str = (
            "# Vacancy\n"
            f"{self._render_vacancy_summary(vacancy_model)}\n\n"
            "# Job description\n"
            f"{vacancy_model.description}\n\n"
            "# Resume\n"
            f"{resume}\n\n"
            "Write the cover letter now."
        )

        system_message: ChatCompletionSystemMessage = ChatCompletionSystemMessage(
            role="system", content=base_system
        )
        user_message: ChatCompletionUserMessage = ChatCompletionUserMessage(
            role="user",
            content=[ChatCompletionTextObject(type="text", text=user_text)],
        )
        return [system_message, user_message]

    __chat_system_prompt: str = (
        "You are an assistant that helps the user refine an existing cover letter"
        " for a job application, turn by turn.\n"
        "You are given the vacancy, the user's resume, the desired tone, and the"
        " CURRENT letter. The user will either ask you to change the letter or ask"
        " a question about it.\n"
        "Respond with a single JSON object with exactly these fields:\n"
        '- "reply": a short message to the user (one or two sentences), in the'
        " same language they wrote in — e.g. describing what you changed, or"
        " answering their question.\n"
        '- "letter": set this ONLY when the user explicitly asks you to change,'
        " edit, rewrite, shorten, expand or otherwise modify the letter — then"
        " put the FULL revised letter body here as a string. In EVERY other case"
        " — a question, a comment, a greeting, a request for your opinion — you"
        ' MUST set "letter" to null and leave the letter untouched. When unsure,'
        " set it to null.\n"
        "Examples:\n"
        '- User: "сделай короче" -> {"reply": "Сократил.", "letter": "<new letter>"}\n'
        '- User: "какой тон у письма?" -> {"reply": "Тон формальный.", "letter": null}\n'
        "Output ONLY that JSON object — no markdown, no code fences, no extra text.\n"
        "Rules for the letter body itself:\n"
        "- Keep the same language as the current letter / job description.\n"
        "- Use vacancy fields verbatim; never insert bracketed placeholders like"
        " [Company] or [Your name] — omit unknown details instead.\n"
        "- Do not invent qualifications absent from the resume.\n"
        '- Put the full letter in the "letter" field every time you revise it,'
        " not a diff or a fragment."
    )

    def build_letter_chat_messages(
        self,
        vacancy_model: VacancyAPISchema,
        resume: str,
        style: str,
        current_letter: str,
        history: Sequence[tuple[str, str]],
        user_message: str,
        system_prompt: str | None = None,
    ) -> List[AllMessageValues]:
        base_system: str = (
            system_prompt if system_prompt is not None else self.__chat_system_prompt
        )
        if style.strip():
            base_system = (
                f"{base_system}\n\nTone and style of the letter: {style.strip()}."
            )

        context_text: str = (
            "# Vacancy\n"
            f"{self._render_vacancy_summary(vacancy_model)}\n\n"
            "# Job description\n"
            f"{vacancy_model.description}\n\n"
            "# Resume\n"
            f"{resume}\n\n"
            "# Current letter\n"
            f"{current_letter}"
        )

        messages: List[AllMessageValues] = [
            ChatCompletionSystemMessage(role="system", content=base_system),
            ChatCompletionSystemMessage(role="system", content=context_text),
        ]
        for role, content in history:
            if role == "assistant":
                messages.append(
                    ChatCompletionAssistantMessage(role="assistant", content=content)
                )
            else:
                messages.append(
                    ChatCompletionUserMessage(
                        role="user",
                        content=[ChatCompletionTextObject(type="text", text=content)],
                    )
                )
        messages.append(
            ChatCompletionUserMessage(
                role="user",
                content=[ChatCompletionTextObject(type="text", text=user_message)],
            )
        )
        return messages

    def _render_vacancy_summary(self, vacancy_model: VacancyAPISchema) -> str:
        fields: list[tuple[str, str | None]] = [
            ("Position", vacancy_model.title),
            ("Company", vacancy_model.company_name),
            ("Salary", vacancy_model.salary),
            ("Location", vacancy_model.work_location),
            ("Work format", self._join_work_formats(vacancy_model.work_formats)),
            (
                "Employment type",
                self._join_employment_types(vacancy_model.employment_types),
            ),
            ("Required experience", vacancy_model.work_experience),
        ]
        lines: list[str] = [f"- {label}: {value}" for label, value in fields if value]
        return "\n".join(lines)

    @staticmethod
    def _join_work_formats(formats: list[WorkFormat]) -> str | None:
        known: list[str] = [f.value for f in formats if f != WorkFormat.UNKNOWN]
        return ", ".join(known) if known else None

    @staticmethod
    def _join_employment_types(types: list[EmploymentType]) -> str | None:
        known: list[str] = [t.value for t in types if t != EmploymentType.UNKNOWN]
        return ", ".join(known) if known else None

    def build_ping(self) -> List[AllMessageValues]:
        return [
            ChatCompletionUserMessage(
                role="user",
                content=[ChatCompletionTextObject(type="text", text="ping")],
            )
        ]
