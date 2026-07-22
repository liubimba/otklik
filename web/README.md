# Лендинг Otklik

Одностраничный сайт проекта: [liubimba.github.io/otklik](https://liubimba.github.io/otklik/).
Next.js 16 (App Router), Tailwind 4, shadcn. Серверной логики нет, поэтому
собирается статическим экспортом в `out/`.

Пакеты ставятся через npm: этот воркспейс не входит в корневой pnpm-workspace,
у него свой `package-lock.json`.

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # статический экспорт в out/
```

## basePath

GitHub Pages отдаёт проектный сайт из подпути `/otklik`, локальный dev-сервер из
корня. Префикс приходит переменной `NEXT_PUBLIC_BASE_PATH` на этапе сборки и
инлайнится в бандл:

```bash
NEXT_PUBLIC_BASE_PATH=/otklik npm run build
```

Есть две ловушки, из-за которых ссылки на файлы из `public/` идут через
`asset()` из `src/lib/asset.ts`, а не пишутся напрямую:

- `next/link` префикс подставляет сам, а `next/image` в Next 16 нет. Об этом
  прямо сказано в `node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/basePath.md`.
- Инлайновый `background-image: url(...)` не префиксуется ничем.

Обе ломаются только в проде на подпути, локально всё выглядит нормально.

## Проверки

```bash
npm run lint
npm run check:contrast
npm run check:fonts
uv run --project ../services/backend python scripts/verify-page.py [порт]
```

`verify-page.py` ходит по поднятому серверу и проверяет якоря, гидратацию и
кадры скриншотов.

Скриншоты приложения генерирует `npm run gen:screens`.

## Деплой

Автоматический: `.github/workflows/pages.yml` собирает экспорт и публикует его
на GitHub Pages при пуше в `main`, если менялось что-то в `web/`. Префикс путей
воркфлоу берёт из `actions/configure-pages`, руками он нигде не записан.
