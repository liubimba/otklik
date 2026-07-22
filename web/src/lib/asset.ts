const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function asset(publicPath: string): string {
	return `${basePath}${publicPath}`;
}
