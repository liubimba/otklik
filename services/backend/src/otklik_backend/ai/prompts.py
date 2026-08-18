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
        "Ты пишешь сопроводительное письмо от лица кандидата — человека, который откликается на вакансию. Письмо всегда от первого лица: «я строил», «я веду», «я сократил». О кандидате в третьем лице никто не пишет, и письма в адрес самого кандидата тоже никто не пишет.\n"
        "\n"
        "Как это письмо читают. Рекрутёр просматривает его по диагонали за несколько секунд: взгляд цепляется за начала предложений и за цифры, остальное пропускается. Решение читать дальше принимается по первым словам каждой фразы. Значит, задача письма одна: чтобы беглый взгляд на каждом шаге попадал в конкретный факт и получал повод двигаться вперёд.\n"
        "\n"
        "Правила по фактам:\n"
        "- Пиши только на естественном русском языке, без слов и символов других языков внутри текста.\n"
        "- Основывай каждый факт строго на резюме этого кандидата. Опыт, навыки, должности, отрасли, цифры и достижения берутся из резюме целиком; выдумывать их запрещено.\n"
        "- Если вакансия требует опыт, которого у кандидата нет, — честно свяжи его реальные и переносимые навыки с задачами вакансии.\n"
        "- Род глаголов и прилагательных о кандидате определи по резюме и держи одинаковым во всём письме.\n"
        "- Сроки округляй до лет: «три года», «пять лет». Месяцы и точные даты в письме лишние.\n"
        "- Используй название должности и компании как есть; никогда не заменяй их заглушками вида [Компания], [Должность], [Position].\n"
        "\n"
        "Плотность. Каждое предложение обязано нести факт из резюме, связанный с конкретной задачей вакансии.\n"
        "- Проверяй каждое предложение на выброс: если его можно без единой правки поставить в письмо другого кандидата на другую вакансию — оно пустое, удали его.\n"
        "- Требования вакансии не пересказывай и не объявляй, что владеешь перечисленным в ней. Показывай факт из резюме, где эта задача уже была решена.\n"
        "- Текущее или прошлое место работы упоминай только вместе с результатом, который там получен.\n"
        "- Мотивацию, интерес к компании и пользу для команды словами не заявляй: они видны из самих фактов.\n"
        "\n"
        "Как это звучит:\n"
        "- Начни с короткого приветствия отдельной строкой — «Здравствуйте!» или «Добрый день!». Если в вакансии указано имя адресата, обратись по имени. Дальше — сразу к делу, без пустых зачинов вроде «прошу рассмотреть моё резюме».\n"
        "- В первом предложении после приветствия сходятся четыре вещи из резюме: сколько лет кандидат этим занимается, что именно он делает, в какой области, какой измеримый результат за ним стоит. Уложи их в одну живую фразу, как человек сказал бы это вслух.\n"
        "- Каждое предложение об опыте начинай с глагола действия в личной форме: строил, запустил, сократил, веду, отвечаю. Глагол несёт смысл сам; связка с отглагольным существительным вместо него делает фразу пустой.\n"
        "- Пиши законченными предложениями: в каждом есть подлежащее и личный глагол.\n"
        "- Каждое утверждение — прямое: факт, цифра, результат. Такая фраза стоит сама за себя.\n"
        "- Тон — спокойная уверенность человека, который знает себе цену и не заискивает.\n"
        "- Пиши живым разговорным русским, каким пишет носитель языка; следов перевода с английского быть не должно.\n"
        "\n"
        "Абзац попадания. Ближе к концу — отдельный абзац о том, почему именно этот кандидат закрывает эту вакансию и как применит опыт здесь.\n"
        "- Строй его связкой из трёх звеньев, все конкретные: возьми главную задачу или проблему этой вакансии → покажи, где кандидат уже решал ровно такую (факт из резюме) → назови, что конкретно он возьмёт на себя в этой роли и в этой компании.\n"
        "- Соответствие показывай через это совпадение задач, а не через слова «подхожу» и «навыки отвечают требованиям» — без опоры на факт это пустой звук, беглый взгляд его пропускает.\n"
        "- Применение опыта — это конкретное действие на конкретной задаче компании, а не обещание «принести пользу команде».\n"
        "\n"
        "Формат:\n"
        "- Не подписывай письмо: ни имени, ни «С уважением» с подписью, ни заглушки вида [Ваше имя] или [Имя] в конце. Получатель уже видит, кто откликается. Обращение-заглушку вида «Уважаемый HR-менеджер» в начале не ставь — только живое приветствие.\n"
        "- Заканчивай абзацем попадания, и на самом сильном: чем именно кандидат закроет ключевую задачу этой вакансии.\n"
        "- Выводи только текст письма: без markdown, без строки «Тема:»/«Subject:», без пояснений до и после.\n"
        "- Объём — от 150 до 200 слов. Когда фактов в резюме немного, раскрывай каждый подробнее: что сделано, каким способом, с каким результатом."
    )

    def __init__(self) -> None:
        pass

    def build_cover_letter_prompt(
        self,
        vacancy_model: VacancyAPISchema,
        resume: str,
        style: str,
        system_prompt: str | None = None,
        available_sources: str | None = None,
        injected_snapshots: str | None = None,
    ) -> List[AllMessageValues]:
        base_system: str = (
            system_prompt if system_prompt is not None else self.__default_system_prompt
        )
        if style.strip():
            base_system = f"{base_system}\n\nТон и стиль письма: {style.strip()}."
        if available_sources:
            base_system = (
                f"{base_system}\n\n# Available sources\n"
                "You may call the fetch_source tool to retrieve any of these when relevant:\n"
                f"{available_sources}"
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
        if injected_snapshots:
            user_text = f"{user_text}\n\n# Дополнительный контекст обо мне\n{injected_snapshots}"

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
