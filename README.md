# Otklik

[liubimba.github.io/otklik](https://liubimba.github.io/otklik/) ·
[Releases](https://github.com/liubimba/otklik/releases) ·
[Читать по-русски](./README.ru.md)

A desktop app that applies to jobs on [hh.ru](https://hh.ru) for you. It reads a
vacancy, writes a cover letter with an LLM from the job description and your CV,
lets you rework that letter in a chat, and can send the application.

Everything runs on your machine. The project has no server: no accounts, no
telemetry, no cloud. You pay for LLM tokens directly to your own provider with
your own key.

![Otklik](./web/public/app-dark.png)

> **Early version (0.2.x).** Read [Risks](#risks) before installing. It is not
> boilerplate.

## Risks

**hh.ru rules formally prohibit automated applications.** Using this app may get
your account suspended, temporarily or permanently. Use it **at your own risk**
and **not on the hh.ru account your career depends on**. Nobody can promise you
otherwise.

The app works inside your own hh.ru session (you log in by hand, once, in an
ordinary browser window) and does not use the official hh API. Automatic sending
is **off by default** and has to be turned on deliberately.

What the app does to keep the risk down:

- **Conservative limits out of the box.** No more than 30 applications a day and
  5 an hour, with an 800 ms ± 400 ms pause between actions. You can raise these,
  and the more aggressive you get, the more you risk.
- **A normal browser with a normal profile.** Chromium keeps its profile between
  runs, so you log in once and hh does not see a brand new device every time.
- **Captchas go to you, not around you.** When a captcha appears the app stops
  and calls you over. No 2captcha, no anti-captcha: solving them automatically
  is a fast way to turn a temporary block into a permanent one.

On first launch the app shows this warning and asks for explicit consent before
going any further.

## Privacy

- **No server, no accounts, no telemetry.** Your data does not leave your
  machine.
- **Local storage.** Settings, history and the hh session live in `~/.otklik/`
  (SQLite plus a Chromium profile).
- **API keys in the system keychain.** Keys go to the operating system's
  credential store under the name `ai.otklik.app`, not into the database. If no
  keychain is available, which happens on a headless Linux box without
  gnome-keyring or kwallet, the app falls back to `~/.otklik/secrets.json` with
  `0600` permissions and tells you which of the two it ended up using.
- **Your own LLM key.** Requests go straight to your provider: OpenAI,
  Anthropic, a local model through [Ollama](https://ollama.com), anything
  [LiteLLM](https://docs.litellm.ai/docs/providers) speaks. With a cloud model
  the job description and your CV are sent to that provider's API, which is the
  price of good generation. With Ollama nothing leaves the machine at all.

## What it does

- Finds hh.ru vacancies by a search query.
- Writes a cover letter from the job description, your CV and your notes on tone
  and content.
- Gives you a chat per letter, to rewrite it, shorten it or change its tone.
- Sends the application, either by a button or automatically (off by default).

Letter generation and the chat are useful on their own, with auto-send left off.

## Install

Installers for Windows and Linux are on the
[Releases](https://github.com/liubimba/otklik/releases) page:

| Platform | Files |
|---|---|
| Windows | `.exe` installer, `.msi` |
| Linux | `.AppImage`, `.deb`, `.rpm` |

There is no macOS build yet. Updates are signed and install themselves.

### Build from source

You will need Node.js (see `.nvmrc`), pnpm, Rust, and Python with
[uv](https://docs.astral.sh/uv/).

```bash
pnpm install
cd services/backend && uv sync && cd ../..
pnpm --filter desktop tauri dev
```

## How it is put together

- **Desktop shell:** Tauri 2 (Rust) with a SvelteKit UI.
- **Automation and API:** a local Python backend on FastAPI, shipped alongside
  the app as its own binary.
- **LLM:** LiteLLM, so the provider is picked by a model string and the key is
  yours.

```
apps/desktop      Tauri + Svelte UI
services/backend  local FastAPI backend (parsing, generation, applying)
web               landing page (Next.js)
```

## License

[MIT](./LICENSE). The software is provided as is, without warranty of any kind.
You are responsible for how you use it, hh.ru's rules included.
