export const UPDATER_PROXY_BYPASS = "localhost,127.0.0.1,::1,<local>";

export function resolveUpdaterProxy(
	env: Record<string, string | undefined>,
): string | null {
	const raw =
		env.ALL_PROXY ??
		env.all_proxy ??
		env.HTTPS_PROXY ??
		env.https_proxy ??
		env.HTTP_PROXY ??
		env.http_proxy ??
		"";
	const trimmed = raw.trim();
	if (!trimmed) {
		return null;
	}
	return trimmed
		.replace(/^socks5h:\/\//i, "socks5://")
		.replace(/^socks4a:\/\//i, "socks4://");
}
