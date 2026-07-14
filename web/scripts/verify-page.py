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

            # Ничто декоративное не смеет рисоваться ПОВЕРХ скриншота приложения.
            #
            # Проверяем порядком отрисовки, а не пикселями: снимки кадра «до» и «после»
            # различаются и без всякого перекрытия — пружина параллакса между двумя
            # кадрами ещё доезжает, и кадр смещается на пиксель.
            #
            # elementFromPoint по умолчанию декор тоже не увидит: у него
            # pointer-events: none. Поэтому на время пробы возвращаем свечению
            # реакцию на указатель — hit-test идёт в том же порядке, что и отрисовка,
            # и честно показывает, кто сверху.
            #
            # Ловушка, из-за которой баг и появился: transform создаёт контекст
            # наложения, и z-index, выставленный ВНУТРИ обёртки-параллакса, снаружи
            # не работает — свечение, идущее следующим по DOM, спокойно накрывает кадр.
            probe = await page.add_style_tag(
                content="[data-slot=glow]{pointer-events:auto !important}"
            )
            shots = page.locator("[data-slot=mockup] img").filter(visible=True)
            covered = []
            for i in range(await shots.count()):
                shot = shots.nth(i)
                await shot.scroll_into_view_if_needed()
                await page.wait_for_timeout(120)
                hits = await shot.evaluate(
                    """img => {
                        const r = img.getBoundingClientRect();
                        // Несколько точек по высоте: свечение садится на ВЕРХ кадра,
                        // проба только по центру его не увидит.
                        return [0.1, 0.25, 0.5, 0.8].map(k => {
                            const el = document.elementFromPoint(
                                r.left + r.width / 2, r.top + r.height * k);
                            if (!el || el === img || img.contains(el)) return null;
                            if (el.contains(img)) return null;  // это обёртка кадра
                            return el.getAttribute('data-slot')
                                || el.className.toString().slice(0, 40);
                        }).filter(Boolean);
                    }"""
                )
                covered.extend(hits)
            await probe.evaluate("el => el.remove()")
            if covered:
                errors.append(f"[{name}] поверх скриншота нарисован декор: {covered}")

            # Гигантский тип не смеет вылезать за контейнер. Ловушка: секции
            # закрыты overflow-hidden (иначе повёрнутые плашки дают горизонтальный
            # скролл), и переполнение заголовка не вызывает прокрутку — его просто
            # молча срезает. Поэтому меряем сам заголовок, а не страницу.
            clipped = await page.evaluate(
                """() => [...document.querySelectorAll('h1,h2,h3')]
                     .filter(el => el.offsetParent !== null)
                     .map(el => {
                       const p = el.parentElement.getBoundingClientRect();
                       const e = el.getBoundingClientRect();
                       const over = Math.max(e.right - p.right, el.scrollWidth - el.clientWidth);
                       return over > 1 ? `${el.textContent.slice(0, 24)}… +${Math.round(over)}px` : null;
                     })
                     .filter(Boolean)"""
            )
            if clipped:
                errors.append(f"[{name}] заголовок обрезан: {clipped}")

            stuck = await page.evaluate(
                "[...document.querySelectorAll("
                "'[data-reveal], [data-typed] span, .animate-enter-up, .animate-enter-clip, .animate-appear-zoom')]"
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
