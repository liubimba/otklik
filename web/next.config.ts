import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	images: {
		// В Next 16 `images.qualities` по умолчанию `[75]`, а `quality` вне списка
		// молча приводится к ближайшему разрешённому — см.
		// node_modules/next/dist/docs/01-app/02-guides/upgrading/version-16.md.
		// Скриншоты приложения — это мелкий текст и волосяные рамки, по которым
		// q=75 заметно мажет, поэтому 90 нужно разрешить явно.
		qualities: [75, 90],
	},
};

export default nextConfig;
