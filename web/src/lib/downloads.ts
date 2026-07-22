import { links } from "@/lib/links";

const RELEASE_API =
	"https://api.github.com/repos/liubimba/otklik/releases/latest";

type ReleaseAsset = {
	name: string;
	browser_download_url: string;
	size: number;
};

export type Download = {
	href: string;
	format: string | null;
	size: number | null;
};

export type Downloads = {
	version: string | null;
	linux: Download;
	windows: Download;
	resolved: boolean;
};

const TO_RELEASES: Download = {
	href: links.releases,
	format: null,
	size: null,
};

const FALLBACK: Downloads = {
	version: null,
	linux: TO_RELEASES,
	windows: TO_RELEASES,
	resolved: false,
};

function formatOf(name: string): string | null {
	const m = name.match(/\.(AppImage|exe|msi|deb|rpm)$/i);
	return m ? m[1] : null;
}

function pick(assets: ReleaseAsset[], pattern: RegExp): Download {
	const asset = assets.find((a) => pattern.test(a.name));
	if (!asset) return TO_RELEASES;
	return {
		href: asset.browser_download_url,
		format: formatOf(asset.name),
		size: asset.size,
	};
}

export async function getDownloads(): Promise<Downloads> {
	const token = process.env.GITHUB_TOKEN;
	try {
		const res = await fetch(RELEASE_API, {
			headers: {
				accept: "application/vnd.github+json",
				...(token ? { authorization: `Bearer ${token}` } : {}),
			},
		});
		if (!res.ok) {
			console.warn(`downloads: GitHub вернул ${res.status}, ведём на релизы`);
			return FALLBACK;
		}
		const release = (await res.json()) as {
			tag_name?: string;
			assets?: ReleaseAsset[];
		};
		const assets = release.assets ?? [];
		const linux = pick(assets, /\.AppImage$/i);
		const windows = pick(assets, /-setup\.exe$/i);
		if (linux === TO_RELEASES || windows === TO_RELEASES) {
			console.warn("downloads: в релизе нет AppImage или exe, ведём на релизы");
			return FALLBACK;
		}
		return {
			version: release.tag_name?.replace(/^v/, "") ?? null,
			linux,
			windows,
			resolved: true,
		};
	} catch (e) {
		console.warn(`downloads: ${e}, ведём на релизы`);
		return FALLBACK;
	}
}

export function humanSize(bytes: number): string {
	return `${Math.round(bytes / 1024 / 1024)} МБ`;
}
