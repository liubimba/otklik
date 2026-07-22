const GITHUB_OWNER = "liubimba";
const GITHUB_REPO = "otklik";

const REPO_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}`;
const LATEST_RELEASE = `${REPO_URL}/releases/latest`;

export const links = {
	github: REPO_URL,
	releases: LATEST_RELEASE,
	issues: `${REPO_URL}/issues`,
	license: `${REPO_URL}/blob/main/LICENSE`,
	ollama: "https://ollama.com",
	litellm: "https://docs.litellm.ai/docs/providers",
} as const;
