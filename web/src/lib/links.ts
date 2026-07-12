const GITHUB_OWNER = "pauldekarin";
// TODO: подтвердить финальное имя репозитория. Автообновление в
// apps/desktop/src-tauri/tauri.conf.json уже смотрит на /otklik, а репозиторий
// пока может называться headhunter_ai — правится здесь, в одном месте.
const GITHUB_REPO = "otklik";

const REPO_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}`;
// Релизы ещё не опубликованы — ссылка будет пустой до первой сборки.
const LATEST_RELEASE = `${REPO_URL}/releases/latest`;

export const links = {
	github: REPO_URL,
	releases: LATEST_RELEASE,
	issues: `${REPO_URL}/issues`,
	license: `${REPO_URL}/blob/main/LICENSE`,
	download: {
		linux: LATEST_RELEASE,
		macos: LATEST_RELEASE,
		windows: LATEST_RELEASE,
	},
	ollama: "https://ollama.com",
	litellm: "https://docs.litellm.ai/docs/providers",
} as const;
