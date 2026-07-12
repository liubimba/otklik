"""Проверка лендинга по критериям приёмки из спеки.

Запуск (из web/, прод-сервер уже поднят):
    uv run --project ../services/backend python scripts/verify-page.py [порт]
"""

import asyncio
import sys

from patchright.async_api import async_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "3000"
URL = f"http://localhost:{PORT}"
OUT = "/tmp/otklik-final"

HYDRATION = ("hydration", "did not match", "text content does not match")
ANCHORS = [
    "#how-it-works",
    "#step-1",
    "#step-2",
    "#step-3",
    "#step-4",
    "#step-5",
    "#features",
    "#privacy",
    "#risks",
    "#pricing",
    "#download",
]


async def main() -> None:
    errors: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        async def run(theme: str, width: int, *, reduced: bool = False) -> None:
            name = f"{theme}-{width}" + ("-reduced" if reduced else "")
            ctx = await browser.new_context(
                viewport={"width": width, "height": 900},
                reduced_motion="reduce" if reduced else "no-preference",
            )
            page = await ctx.new_page()

            # patchright ломает add_init_script (инжектит через внутренний запрос,
            # который отдаёт 503 и оставляет пустую страницу) — сеем тему визитом + reload.
            await page.goto(URL, wait_until="domcontentloaded")
            await page.evaluate(f"localStorage.setItem('theme', '{theme}')")

            page.on("pageerror", lambda e: errors.append(f"[{name}] pageerror: {e}"))

            def on_console(m):
                if m.type == "error":
                    errors.append(f"[{name}] console.error: {m.text[:140]}")
                if any(h in m.text.lower() for h in HYDRATION):
                    errors.append(f"[{name}] HYDRATION: {m.text[:140]}")

            page.on("console", on_console)
            await page.reload(wait_until="networkidle")

            if not reduced:
                await page.evaluate(
                    "async () => { const step = innerHeight * 0.6;"
                    " for (let y = 0; y < document.body.scrollHeight; y += step) {"
                    "   scrollTo(0, y); await new Promise(r => setTimeout(r, 140)); }"
                    " scrollTo(0, document.body.scrollHeight);"
                    " await new Promise(r => setTimeout(r, 1500)); }"
                )
            await page.wait_for_timeout(1500)

            if await page.evaluate(
                "document.documentElement.scrollWidth > window.innerWidth + 1"
            ):
                errors.append(f"[{name}] горизонтальный скролл")

            missing = await page.evaluate(
                f"{ANCHORS!r}.filter(a => !document.querySelector(a))"
            )
            if missing:
                errors.append(f"[{name}] не резолвятся якоря: {missing}")

            wrong = await page.evaluate(
                "[...document.querySelectorAll('[data-slot=mockup] img')]"
                ".filter(i => i.offsetParent !== null)"
                ".map(i => i.getAttribute('src'))"
                f".filter(s => !s.includes('{theme}'))"
            )
            if wrong:
                errors.append(f"[{name}] скриншот чужой темы: {wrong}")

            visible = await page.evaluate(
                "[...document.querySelectorAll('[data-slot=mockup] img')]"
                ".filter(i => i.offsetParent !== null).length"
            )
            if visible != 6:  # hero + 5 шагов
                errors.append(f"[{name}] видимых скриншотов {visible}, ожидалось 6")

            if not reduced:
                broken = await page.evaluate(
                    "[...document.images].filter(i => i.offsetParent !== null)"
                    ".filter(i => !i.complete || i.naturalWidth === 0)"
                    ".map(i => i.getAttribute('src'))"
                )
                if broken:
                    errors.append(f"[{name}] битые картинки: {broken}")

            stuck = await page.evaluate(
                "[...document.querySelectorAll("
                "'[data-reveal], [data-typed] span, .animate-enter-up, .animate-enter-clip')]"
                ".filter(e => parseFloat(getComputedStyle(e).opacity) < 0.99).length"
            )
            if stuck:
                errors.append(f"[{name}] {stuck} элементов остались с opacity < 1")

            await page.screenshot(path=f"{OUT}-{name}.png", full_page=True)
            await ctx.close()

        for theme in ("dark", "light"):
            for width in (1440, 375):
                await run(theme, width)
        await run("dark", 1440, reduced=True)  # всё видно БЕЗ скролла

        # Интерактив демо-чата не сломан
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        letter = page.locator("[data-typed]")
        await letter.scroll_into_view_if_needed()
        await page.wait_for_timeout(3500)
        base = (await letter.inner_text()).strip()
        await page.get_by_role("button", name="Сделай короче").click()
        await page.wait_for_timeout(4000)
        if (await letter.inner_text()).strip() == base:
            errors.append("демо-чат: письмо не переписалось")
        await page.get_by_role("button", name="Вернуть исходное письмо").click()
        await page.wait_for_timeout(3500)
        if (await letter.inner_text()).strip() != base:
            errors.append("демо-чат: исходное письмо не вернулось")
        await browser.close()

    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("OK — все критерии приёмки выполнены")


asyncio.run(main())
