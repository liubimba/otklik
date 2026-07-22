# Otklik landing page

The project's single page site: [liubimba.github.io/otklik](https://liubimba.github.io/otklik/).
Next.js 16 (App Router), Tailwind 4, shadcn. There is no server-side logic, so
it is built as a static export into `out/`.

Packages are installed with npm. This workspace is not part of the root pnpm
workspace and keeps its own `package-lock.json`.

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # static export into out/
```

## basePath

GitHub Pages serves a project site from the `/otklik` sub-path while the local
dev server serves it from the root. The prefix arrives as
`NEXT_PUBLIC_BASE_PATH` at build time and is inlined into the bundle:

```bash
NEXT_PUBLIC_BASE_PATH=/otklik npm run build
```

Two traps are the reason every path into `public/` goes through `asset()` from
`src/lib/asset.ts` instead of being written out directly:

- `next/link` applies the prefix on its own, `next/image` in Next 16 does not.
  Its own documentation says so, in
  `node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/basePath.md`.
- An inline `background-image: url(...)` is prefixed by nothing at all.

Both break only in production on the sub-path. Locally everything looks fine.

## Download buttons

The buttons in the final section link to the installers themselves rather than
to the releases page. Asset names carry the version, so there is no permanent
URL to write down, and the one stable name in a release, `latest.json`, is
served without CORS headers, so the browser cannot read it either.

So `src/lib/downloads.ts` asks the GitHub API while the page is being
generated, and the direct links end up in the HTML. No JavaScript at runtime,
no rate limit. If the API is unreachable the build does not fail, it falls back
to the releases page, and a gate in the workflow then fails the run, because a
silent fallback looks exactly like success.

The links go stale when a release ships, which is why the workflow rebuilds on
`release: published` as well as on a push.

## Checks

```bash
npm run lint
npm run check:contrast
npm run check:fonts
uv run --project ../services/backend python scripts/verify-page.py [port]
```

`verify-page.py` drives a running server and checks anchors, hydration and the
screenshot frames. `check:contrast` reads the tokens out of `globals.css` and
computes WCAG ratios, following a `var()` reference when a token points at
another one.

`npm run gen:screens` generates the application screenshots.

## Icon

`src/app/favicon.ico` is a copy of `apps/desktop/src-tauri/icons/icon.ico`, and
`src/app/apple-icon.png` is the same drawing resized to 180×180. Change the
application icon and both need updating.

The `<head>` links are written by Next through its App Router file convention,
so `basePath` is applied to them automatically. Do not add an `icon.png` next
to the `.ico`: Next then stops emitting a link to `favicon.ico`, and on a
sub-path the browser would look for an icon at the domain root, where there is
none.

## Deploy

`.github/workflows/pages.yml` builds the export and publishes it to GitHub
Pages on a push to `main` that touches `web/`, and on a published release. The
path prefix comes from `actions/configure-pages`, so it is never written down
by hand.
