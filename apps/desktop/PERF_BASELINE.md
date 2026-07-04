# Frontend Perf Baseline

Живой журнал для перф-профайлинга апы. Данные снимаются WebKit Web
Inspector (Tauri Linux). Traces хранятся в
`apps/desktop/src-tauri/scenarios/*.json` (гит-игнорить не забывать —
они тяжёлые).

Как снять baseline:

1. `pnpm tauri dev` в `apps/desktop/`.
2. Открыть окно, Ctrl+Shift+I → DevTools.
3. Для каждого сценария ниже:
   - **Performance panel** → Record 10 c → воспроизвести действие → Stop.
   - Long tasks (>50 ms) считать из панели «Bottom-Up» → sort by Self Time.
   - Network requests — Network panel, фильтр `api/v1`, счётчик записей.
   - Peak heap — Memory panel → Heap snapshot, значение «JS heap size».
   - Drag FPS — Rendering panel → FPS meter, средняя цифра во время
     активного взаимодействия.

Строки заполняются в двух состояниях: **baseline** (до Phase C) и
**after** (после фиксов Phase C). Дельту прикидывать на глаз — 30% и
выше на любой метрике — заметная победа.

---

## Snapshot — 2026-07-03 (2-й замер, Screenshots off) — root cause: software rendering

Пересняли 4 сценария уже **без** Screenshots instrument'а. Фризы
визуально остались, и теперь traces показывают их честно.

| Сценарий | Duration | frames | avg | max | >100ms | paint total |
|----------|----------|--------|-----|-----|--------|-------------|
| auto-submit    | 36.8 s | 372 | 85 ms | 192 ms | 196 | **31.2 s (85%)** |
| drag resize    |  8.6 s | 187 | 37 ms | 234 ms | 31  | 6.8 s (79%) |
| regenerate     |  5.2 s |  98 | 32 ms | 231 ms | 14  | 2.8 s (55%) |
| sidebar toggle |  5.7 s | 138 | 26 ms | 246 ms | 15  | 3.4 s (60%) |

Ключевые факты:

1. **Каждый paint — full window** (`2494×1061` в sidebar/regenerate,
   `1988×957` в auto-submit — размер окна на момент записи). Ни одного
   partial-repaint quad'а во всех 4 traces. WebKit не может ограничить
   перерисовку изменённой областью.
2. **Каждый full-window paint ≈ 220 ms.** 2.6 M пикселей за 220 ms —
   это скорость software rasterization (~12 Mpx/s), не GPU.
3. **JS не при чём**: script total за trace — 120–200 ms, самый долгий
   одиночный event — 34 ms. Layout — единицы ms. forced-layout — 2–8
   событий, до 66 ms суммарно (не главный фактор).
4. Sidebar toggle: CSS `transition-[width] duration-200` порождает
   paint burst на **4 секунды** (2 клика × ~2 s) — software рендер
   выдаёт ~4.5 fps, transition кончается за 200 ms, а paint queue
   разгружается ещё секунды.

**Вывод: WebKitGTK рендерит в software mode (GPU compositing
неактивен).** Это переводит любую CSS-анимацию/transition в
full-window software repaint по 220 ms. Все прошлые app-level фиксы
(backdrop-blur removal, contain, batch invalidate) валидны, но
неощутимы, пока каждый кадр стоит 220 ms.

## Snapshot — 2026-07-03 (3-й заход): автоматизированная диагностика, root cause найден

Собран собственный тест-харнесс (Playwright с Tauri не работает —
не умеет подключаться к WebKitGTK-webview):

- **AT-SPI** (accessibility bus) кликает по кнопкам приложения
  программно — работает на Wayland без фокуса и без X-событий
  (`scratchpad/atspi_toggle.py`, `atspi_click.py`).
- **xwd-хэш семплирование ~30 Hz** считает реально показанные кадры
  (только X11/XWayland инстансы).
- **/proc per-thread CPU** атрибуция по тредам webprocess.

### Меренные факты

1. **Фриз подтверждён и измерен**: на каждый sidebar-toggle экран
   меняется всего 2 раза — старт и (через ~300-350 ms fullscreen)
   финал. CSS-transition 200 ms не показывает ни одного
   промежуточного кадра.
2. **Масштабируется с площадью окна**: 91 ms (800×600) → 330 ms
   (2494×1371) на XWayland. Это растеризация, не фикс. sync-stall.
3. **Не зависит от контента**: settings-страница фризит так же, как
   queue со списком вакансий. Виртуализация списка не поможет.
4. **Вся работа — на main thread webprocess**: ~640 ms CPU/toggle
   fullscreen; Skia painting-треды не участвуют. Поэтому фриз, а
   не просто нагрузка.
5. **Root cause — связка WebKitGTK 2.52 + NVIDIA EGL (driver
   575.64)**. A/B на Wayland-native (800×600):
   - NVIDIA EGL (дефолт): main **245 ms/toggle**, total 246 ms
   - Форс Mesa EGL (`__EGL_VENDOR_LIBRARY_FILENAMES=...50_mesa.json`):
     main **6 ms/toggle** (фриза нет!), но total **2315 ms/toggle** —
     llvmpipe жжёт все ядра (печка/батарея).
   Вероятный механизм NVIDIA-пути: CPU-растр/ридбек в VRAM-backed
   GBM-буфер через PCIe (uncached) — по ~200+ ms на full-window кадр.
6. Все `WEBKIT_*` рычаги на XWayland — no-op (llvmpipe там из-за
   отсутствия DRI3; отдельная системная проблема — GLX по умолчанию
   уходит в llvmpipe, NVIDIA доступна только с PRIME-offload vars).
7. Прошлые app-фиксы (backdrop-blur, contain, batch invalidate)
   валидны, но не ощущаются, пока каждый кадр стоит 200+ ms.

### Что осталось проверить (недогнанная батарея, Wayland-native)

`WEBKIT_DISABLE_DMABUF_RENDERER=1`, `WEBKIT_DMABUF_RENDERER_FORCE_SHM=1`,
`WEBKIT_DMABUF_RENDERER_DISABLE_GBM=1`, `WEBKIT_SKIA_ENABLE_CPU_RENDERING=1`
— скрипт готов: `scratchpad/wayland_final.sh`. Цель: main ≤ 20 ms/toggle
И total ≤ ~300 ms/toggle.

### Рекомендации

1. Догнать батарею выше; если FORCE_SHM/DISABLE_GBM дают целевые
   числа — прописать env-var в `src-tauri` (до создания webview).
2. App-level страховка независимо от системного фикса: убрать
   full-window анимации — `transition-[width]` в
   `sidebar/sidebar.svelte:76,87` (snap вместо анимации), т.к. на
   этом стеке любой full-window кадр стоит 200+ ms.
3. Системно: разобраться, почему GLX/EGL по умолчанию не видят
   NVIDIA (prime-select / glvnd конфиг); обновление WebKitGTK
   (>2.52) может исправить NVIDIA-путь.

---

### Следующий шаг — диагностика GPU compositing (устарело, см. выше)

1. Запустить и проверить руками (фризы должны уйти):
   `WEBKIT_DISABLE_COMPOSITING_MODE=0 WEBKIT_DISABLE_DMABUF_RENDERER=0 pnpm tauri dev`
   (часто на Linux/NVIDIA помогает наоборот `WEBKIT_DISABLE_DMABUF_RENDERER=1` —
   dmabuf-рендерер бывает сломан на проприетарных драйверах; проверить оба варианта).
2. Если compositing заведётся — зафиксировать env-var в Tauri
   (`tauri.conf.json` или в main.rs через `std::env::set_var` до
   создания webview) и переснять traces: ожидание — paint quad'ы
   станут маленькими (дельта-регионы), slow frames уйдут.
3. Если GPU включить не удаётся (драйвер/Wayland) — план Б, резать
   стоимость кадра: убрать `transition-[width]` из
   `sidebar/sidebar.svelte:76,87`, `transition-all` из
   `sidebar-rail.svelte:25`, `transition-colors` с resize-handle
   sheet'а. Snap вместо анимаций — при software rendering плавность
   всё равно недостижима (4.5 fps).

---

## Snapshot — 2026-07-03 (1-й замер) — traces испорчены Screenshots instrument'ом

Пересняли те же 4 сценария после Phase C.5 (backdrop-blur removal +
`[contain:layout_paint]` на vacancy cards). Пользователь: «фризы
остались точно такие же».

Анализ показал, что traces **не отражают реальную картину** — они
искажены самим профайлером. В `recording.instrumentTypes` включён
`timeline-record-type-screenshots`. WebKitGTK при этом снимает
скриншот окна каждые ~220 ms, и **каждый скриншот — full-window
paint `2494×1061` длительностью ~220 ms**.

Признаки-артефакты (одинаковые во всех 4 сценариях):

| Сценарий | Duration | slow frames >100ms | avg slow-frame ms | JS-time за trace |
|----------|----------|--------------------|-------------------|------------------|
| auto-submit    | 36.3 s | 134 | 224 ms | ~200 ms  |
| drag resize    |  8.3 s |  24 | 220 ms | ~190 ms  |
| regenerate     |  8.7 s |  27 | 220 ms | ~170 ms  |
| sidebar toggle |  8.9 s |  27 | 224 ms | ~121 ms  |

- Все slow frames кластеризуются в 217–254 ms, независимо от сценария.
- Inter-arrival между slow frames = ~220 ms фиксированно (min 214, max 738).
- Каждый paint квада — full window `[0,0,2494,1061]`.
- **JS work за весь trace всего 121–200 ms** (script total_ms). То есть
  фризы **не в JavaScript**.

Вывод: 83% времени auto-submit trace = screenshot capture pipeline
WebKit'а, а не работа приложения. Реальные лаги от Phase C.5 фиксов,
если и есть, полностью замаскированы 4.5 Гц loop'ом снимков.

### Что делать дальше

1. В WebKit Web Inspector → Timeline снять галку **Screenshots**
   (иконка камеры вверху панели). Пересрать те же 4 сценария.
2. С чистыми traces проанализировать реальные long tasks (>50 ms) —
   тогда будет видно, что действительно тормозит.

### Остальные smell'ы, видные даже сквозь screenshot noise

**scenario_regenerate — 1 клик Regenerate = 11 API + 22 IPC log calls.**
На 8.7-сек trace: 2× POST `/application/generate` (двойной триггер?),
5× GET `/application`, 4× GET `/application/letters`. Цепочка
`letter_pending → letter_ready → letter_sent` даёт 2 invalidate × 3
события = 6 refetch'ей — но 2× generate это отдельный баг: одно
нажатие должно быть 1 request. Расследовать: возможно, mutation
`regenerate` вызывается дважды из-за неснятого `$effect` или из-за
ре-invalidate'а во время in-flight запроса.

**IPC log noise** — 22 `plugin:log|log` вызовов на 8.7 сек. Каждый
`getLogger().info(...)` в `client.ts:15` идёт через Tauri IPC. Мелочь,
но при массовом парсинге вакансий (auto-submit storm) может ощутимо
загружать WebKit ↔ Rust bridge. Дешёвый фикс: в prod build изменить
log-level на warn+ или batch'ить логи.

## Snapshot — 2026-07-02, после Phase C (устарел, был снят с тем же артефактом)

Замеры сняты через WebKit Web Inspector (Tauri WebKitGTK на Linux)
уже после применения Phase C. Формат traces: WebKit timeline JSON,
парсинг через `jq`.

Сводка (avg frame ms → FPS; slowest frame; Main Thread CPU avg;
network requests):

| Scenario                      | Duration | avg frame | slowest frame | Main CPU | HTTP / IPC |
|-------------------------------|----------|-----------|---------------|----------|------------|
| 1. auto-submit storm          | 58.9 s   | 37 ms     | **77 ms**     | **82 %** | 5 API + 8 log-ipc + 2 fs-ipc |
| 2. drag resize sheet          | 7.5 s    | ~18 ms    | 8.9 ms        | 70 %     | 0          |
| regenerate letter (Ctrl+R)    | 7.5 s    | 21 ms     | **441 ms** ⚠ | 54 %     | 5 API + 10 log-ipc |
| sidebar toggle                | 5.2 s    | 36 ms     | **286 ms** ⚠ | 75 %     | 0          |

Ключевые findings:

1. **HIGH — Sidebar toggle: 4 подряд frames по 240-286 ms.** Простой
   toggle sidebar'а вырывает Main Thread на ~1 с. `transition-[width]
   duration-200` в `sidebar/sidebar.svelte:76,87` + `transition-[width,
   height, padding]` в `sidebar-menu-button.svelte:5` тянут за собой
   reflow всей Sidebar.Inset области (queue-page с vacancy list'ом
   без виртуализации).
2. **HIGH — Regenerate click: одиночный frame 441 ms.** Клик по
   «Сгенерировать заново» блокирует UI на ~440 ms. Из-за него click
   event сам стоит 71 ms, вслед за ним microtask на 69 ms
   (TanStack invalidate chain + refetch scheduling). После моих Phase
   C фиксов улучшение относительно предыдущего гипотетического
   baseline'а есть, но всё ещё явно ощутимо.
3. **MEDIUM — auto-submit storm держит Main CPU 82 % avg 59 сек** +
   stable 73-77 ms frames. HTTP-фиксы (Phase C.1) сделали своё:
   всего 5 API-вызовов за минуту вместо десятков. Оставшаяся
   нагрузка — рендер (872 recalc-styles, 892 paints, 4 forced-layout
   в цикле).
4. **MEDIUM — Layout thrashing.** `forced-layout` встречается в
   auto-submit (4×) и regenerate (5×). Синхронный layout из JS
   обычно значит: код читает `getBoundingClientRect` / `offsetWidth`
   после мутации DOM. Не найдено в наших effect'ах — вероятно в
   bits-ui / Tooltip primitive'ах при hover'е (см. pointerenter
   58 ms в scenario 1).

## Root cause — 441 ms regenerate frame

Deep-dive scenario_regenerate.json (window t=928.68…929.12):
- **script** events всего 42 в этом окне, самый долгий — message (WS
  event) 7 ms, microtask 5 ms. JS не в вине.
- **paint** — два подряд события длительностью **221 ms + 217 ms
  ≈ 438 ms**, покрывающие весь frame.

Прямая причина: `sheet-overlay.svelte:15` содержала
`supports-backdrop-filter:backdrop-blur-xs`. WebKitGTK на Tauri Linux
composit'ит и blur'ит все пиксели за overlay каждый кадр — а под
overlay в момент click'а виден queue-page список. Один backdrop-blur =
две paint-фазы по 200+ ms.

Fix (Phase C.5.c): `sheet-overlay.svelte` — убрал класс
`supports-backdrop-filter:backdrop-blur-xs`. `bg-black/10` остался как
диммер. Модалка визуально остаётся отличимой от контента без blur.

Fix (Phase C.5.b): `vacancy-card.svelte` — добавлен `[contain:layout_paint]`.
При sidebar-transition WebKit больше не разбегается по всему списку —
каждая карточка держит свой reflow локально.

## Не критично прямо сейчас, но зафиксировать
- `pointerenter 58 ms` в auto-submit — hover на элемент со скрытой
  анимацией, вероятно sidebar-menu-button tooltip портал.
- WebKit trace через IPC log plugin — 10 IPC log вызовов на 7.5 сек
  regenerate'а. `getLogger()` пишет через `plugin:log|log` каждое
  info. Мелочь, но при массовом парсинге может суммироваться.

---

## Scenario 1: Auto-submit storm

Открыть letter-review-sheet для новой вакансии, включить `auto_submit` в
settings, запустить парсинг на 5-10 вакансий, дождаться завершения
последней submission. Запись — с момента клика "Новый поиск" до момента,
когда последняя вакансия перешла в LETTER_SENT.

| Metric              | Baseline | After Phase C | Notes |
|---------------------|----------|---------------|-------|
| Long tasks (>50ms)  |          |               |       |
| Network requests    |          |               | `api/v1` |
| Peak JS heap (MB)   |          |               |       |
| Scripting time (ms) |          |               |       |

---

## Scenario 2: Drag resize sheet

Открыть sheet, поймать курсор на левой полоске (cursor: ew-resize),
драгать sheet 5 секунд туда-обратно.

| Metric               | Baseline | After Phase C | Notes |
|----------------------|----------|---------------|-------|
| Avg FPS during drag  |          |               | Rendering → FPS meter |
| Layout events count  |          |               | Performance timeline |
| localStorage.setItem calls | |               | Performance → Storage |

---

## Scenario 3: Big vacancy list

Seed 100+ вакансий (либо парсинг, либо прямая вставка в SQLite:
`INSERT INTO vacancies (title, apply_link, description) SELECT 't'||id, 'https://hh.ru/vacancy/'||id, 'd' FROM generate_series(1000, 1200) AS id;`).
Открыть queue page, замерить время до полного рендера. Скроллить список.

| Metric               | Baseline | After Phase C | Notes |
|----------------------|----------|---------------|-------|
| Mount time (ms)      |          |               | Performance → Timings |
| Scroll FPS           |          |               |       |
| Peak JS heap (MB)    |          |               |       |
| DOM nodes count      |          |               | Elements → root count |
