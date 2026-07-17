import { m } from "$lib/paraglide/messages";

const HINTS: ReadonlyArray<[RegExp, () => string]> = [
	[
		/connection refused|ECONNREFUSED|Failed to connect/i,
		m.error_model_unreachable,
	],
	[/401|403|api key|unauthorized/i, m.error_model_bad_key],
	[/credentials not provided/i, m.error_model_missing_credentials],
	[/timeout|timed out/i, m.error_model_timeout],
	[/no deployments configured/i, m.error_model_not_configured],
];

export function explainProviderError(message: string): string {
	for (const [pattern, text] of HINTS) {
		if (pattern.test(message)) return text();
	}
	return message;
}
