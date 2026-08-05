"use client";

import { Maximize2Icon, XIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import { asset } from "@/lib/asset";
import { cn } from "@/lib/utils";

export type Clip = {
	src: string;
	alt: string;
};

export function VideoLightbox({
	src,
	alt,
	className,
}: Clip & { className?: string }) {
	const [open, setOpen] = useState(false);
	const [mounted, setMounted] = useState(false);
	const url = asset(src);

	useEffect(() => {
		setMounted(true);
	}, []);

	useEffect(() => {
		if (!open) return;
		const onKey = (event: KeyboardEvent) => {
			if (event.key === "Escape") setOpen(false);
		};
		document.addEventListener("keydown", onKey);
		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		return () => {
			document.removeEventListener("keydown", onKey);
			document.body.style.overflow = previousOverflow;
		};
	}, [open]);

	return (
		<>
			<button
				type="button"
				onClick={() => setOpen(true)}
				aria-label={`${alt} — открыть крупно`}
				className={cn("group relative block w-full cursor-zoom-in", className)}
			>
				<video
					className="h-auto w-full"
					width={1280}
					height={720}
					autoPlay
					loop
					muted
					playsInline
					preload="metadata"
				>
					<source src={url} type="video/mp4" />
				</video>
				<span className="pointer-events-none absolute right-2 bottom-2 flex items-center gap-1 rounded-md bg-black/65 px-2 py-1 text-xs font-medium text-white opacity-0 transition-opacity group-hover:opacity-100">
					<Maximize2Icon className="size-3.5" aria-hidden="true" />
					Крупно
				</span>
			</button>

			{open &&
				mounted &&
				createPortal(
					<div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm">
						<button
							type="button"
							aria-label="Закрыть"
							onClick={() => setOpen(false)}
							className="absolute inset-0 cursor-zoom-out"
						/>
						<button
							type="button"
							aria-label="Закрыть"
							onClick={() => setOpen(false)}
							className="absolute top-4 right-4 z-10 rounded-full bg-white/10 p-2 text-white transition-colors hover:bg-white/20"
						>
							<XIcon className="size-6" />
						</button>
						<video
							className="relative max-h-[90vh] max-w-[92vw] rounded-lg shadow-2xl"
							controls
							autoPlay
							loop
							muted
							playsInline
						>
							<source src={url} type="video/mp4" />
						</video>
					</div>,
					document.body,
				)}
		</>
	);
}
