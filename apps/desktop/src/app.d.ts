interface ImportMetaEnv {
	readonly VITE_BACKEND_IP: string;
	readonly VITE_BACKEND_PORT: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
