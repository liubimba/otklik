"use client";

import type * as React from "react";

import { useReveal } from "@/hooks/use-reveal";
import { cn } from "@/lib/utils";

/**
 * Клиентская обёртка вокруг серверного содержимого: children — слот, поэтому
 * тело секций остаётся server-rendered, а клиентской становится только эта рамка.
 *
 * data-reveal нужен как страховка: без JS элемент навсегда остался бы
 * прозрачным, поэтому <noscript> в layout.tsx и блок prefers-reduced-motion
 * в globals.css принудительно возвращают ему opacity: 1.
 */
export function Reveal({
	children,
	className,
	delay,
}: {
	children: React.ReactNode;
	className?: string;
	delay?: "delay-100" | "delay-200" | "delay-300";
}) {
	const { ref, revealed } = useReveal<HTMLDivElement>();

	return (
		<div
			ref={ref}
			data-reveal=""
			className={cn(
				revealed ? "animate-appear" : "opacity-0",
				delay,
				className,
			)}
		>
			{children}
		</div>
	);
}
