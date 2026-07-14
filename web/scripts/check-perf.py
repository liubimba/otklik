#!/usr/bin/env python
"""Гейт производительности лендинга.

Ловит ровно тот класс регрессов, который не видно ни на скриншоте, ни в билде:
фон, который красиво выглядит и при этом роняет прокрутку до слайд-шоу.

Мерить нужно ПРОДОВУЮ сборку (`npm run build && npm run start`). Гейт долго ходил
на прибитый :3000, где обычно висит dev-сервер, и мерил его: 8 МБ неминифицированного
JS и полусекундные задачи — это цифры дев-режима, к продовой странице отношения не
имеющие. Порт теперь берётся аргументом, как у verify-page.py.

Что меряется:

1. FPS при скролле всей страницы с 4× замедлением CPU. Эмуляция обязательна:
   на голой машине разработчика тормозов не видно никогда, а у соискателя
   ноутбук на Celeron.
2. Long tasks — задачи главного потока длиннее 200 мс. Одна такая = видимый рывок.
3. CLS: любой сдвиг макета при появлении слоёв.
4. Вес JS: motion не должен незаметно потянуть за собой полбиблиотеки.
5. prefers-reduced-motion: ни одна анимация не крутится.

Запуск:  services/backend/.venv/bin/python web/scripts/check-perf.py [порт]
"""

from __future__ import annotations

import sys

from patchright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "3000"
URL = f"http://localhost:{PORT}"

# Пороги. Не «идеал», а граница, ниже которой страница ощущается сломанной.
MIN_MEDIAN_FPS = 50.0
MAX_LONG_TASK_MS = 200.0
MAX_CLS = 0.02
MAX_JS_KB = 400  # motion ≈ 35 КБ gzip; запас на React/Next и рост страницы

CPU_THROTTLE = 4

# Считаем кадры и long tasks прямо в странице: снаружи это не увидеть.
PROBE = """
window.__perf = { frames: [], longTasks: [], cls: 0 };

let last = performance.now();
function tick(now) {
  window.__perf.frames.push(now - last);
  last = now;
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

new PerformanceObserver((list) => {
  for (const e of list.getEntries()) window.__perf.longTasks.push(e.duration);
}).observe({ type: 'longtask', buffered: true });

new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    if (!e.hadRecentInput) window.__perf.cls += e.value;
  }
}).observe({ type: 'layout-shift', buffered: true });
"""


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def main() -> int:
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- 1-4: скролл под нагрузкой -------------------------------------
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        js_bytes = 0

        def on_response(response):
            nonlocal js_bytes
            if response.request.resource_type == "script":
                try:
                    js_bytes += len(response.body())
                except Exception:
                    pass

        page.on("response", on_response)

        cdp = page.context.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": CPU_THROTTLE})

        page.goto(URL, wait_until="load")
        page.evaluate(PROBE)
        page.wait_for_timeout(800)

        # Скроллим до конца шагами, как это делает человек, а не мгновенным
        # прыжком: рывки живут именно в процессе прокрутки.
        height = page.evaluate("document.body.scrollHeight")
        step = 600
        offset = 0
        while offset < height:
            page.mouse.wheel(0, step)
            offset += step
            page.wait_for_timeout(120)
        page.wait_for_timeout(400)

        perf = page.evaluate("window.__perf")

        # Первые кадры — это ещё загрузка, они не про скролл.
        deltas = [d for d in perf["frames"][20:] if d > 0]
        fps = [1000.0 / d for d in deltas]
        med_fps = median(fps)
        worst_task = max(perf["longTasks"], default=0.0)
        cls = perf["cls"]
        js_kb = js_bytes / 1024

        def check(ok: bool, message: str) -> None:
            print(f"{'✓' if ok else '✗'} {message}")
            if not ok:
                failures.append(message)

        check(
            med_fps >= MIN_MEDIAN_FPS,
            f"медианный FPS при скролле (CPU ×{CPU_THROTTLE}): "
            f"{med_fps:.1f} (порог {MIN_MEDIAN_FPS:.0f})",
        )
        check(
            worst_task <= MAX_LONG_TASK_MS,
            f"худшая задача главного потока: {worst_task:.0f} мс "
            f"(порог {MAX_LONG_TASK_MS:.0f})",
        )
        check(cls <= MAX_CLS, f"CLS: {cls:.4f} (порог {MAX_CLS})")
        check(js_kb <= MAX_JS_KB, f"вес JS: {js_kb:.0f} КБ (порог {MAX_JS_KB})")

        page.close()

        # --- 5: «меньше движения» ------------------------------------------
        reduced = browser.new_context(
            viewport={"width": 1440, "height": 900}, reduced_motion="reduce"
        )
        rpage = reduced.new_page()
        rpage.goto(URL, wait_until="load")

        assert rpage.evaluate(
            "matchMedia('(prefers-reduced-motion: reduce)').matches"
        ), "эмуляция reduced-motion не применилась — проверка была бы фиктивной"

        # На самой загрузке анимации успевают создаться и тут же снимаются правилом
        # `animation: none` — это транзиент в один кадр, а не то, что мы ловим.
        # Ловим установившееся состояние: анимация, которая КРУТИТСЯ и через 3 с.
        running: list[str] = []
        for _ in range(15):
            rpage.wait_for_timeout(200)
            running = rpage.evaluate(
                """() => document.getAnimations()
                     .filter(a => a.playState === 'running')
                     .map(a => a.effect?.target?.className?.toString?.() ?? '?')"""
            )
            if not running:
                break

        ok = len(running) == 0
        print(
            f"{'✓' if ok else '✗'} при prefers-reduced-motion крутящихся анимаций: "
            f"{len(running)}"
        )
        if not ok:
            failures.append(f"анимации не выключены при reduced-motion: {running[:5]}")

        reduced.close()
        browser.close()

    if failures:
        print("\nПроизводительность просела:")
        for f in failures:
            print(f"  — {f}")
        return 1

    print("\nВсе пороги выдержаны.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
