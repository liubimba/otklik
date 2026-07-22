import type { NextConfig } from "next";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
	output: "export",
	basePath,
	images: {
		unoptimized: true,
		qualities: [75, 90],
	},
};

export default nextConfig;
