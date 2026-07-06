from collections.abc import Sequence

from headhunter_backend.api.schemas import VacancyAPISchema, WorkFormat, EmploymentType
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
        "You write personalized cover letters for job applications.\n"
        "Rules:\n"
        "- Write the cover letter in the same language as the job description.\n"
        "- Use the position title, company name and other vacancy fields you are given verbatim — never replace them with bracketed placeholders like [Company] or [Position].\n"
        "- Reference concrete details from the job description and tie them to evidence in the resume.\n"
        "- Do not invent qualifications that are not present in the resume.\n"
        "- Output only the body of the letter. No bracketed placeholders such as [Your name], [Date], [Company address]. If a detail is unknown, omit it instead of inserting a placeholder.\n"
        "- Keep the letter concise (under ~250 words) unless the job description clearly calls for a longer, more formal format."
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
            base_system = (
                f"{base_system}\n\nTone and style of the letter: {style.strip()}."
            )

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
