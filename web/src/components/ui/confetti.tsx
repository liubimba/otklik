"use client";

import {
	motion,
	useReducedMotion,
	useScroll,
	useSpring,
	useTransform,
} from "motion/react";
import { useRef } from "react";

import { cn } from "@/lib/utils";

type Shape = "dot" | "diamond" | "ring";

type Bit = {
	/** Позиция в процентах от секции — не px: секции разной высоты. */
	x: number;
	y: number;
	size: number;
	shape: Shape;
	tone: "brand" | "accent-1" | "accent-2";
	/** Ход параллакса, px. Разные скорости у соседних — это и есть глубина. */
	speed: number;
};

const TONE = {
	brand: "bg-brand",
	"accent-1": "bg-accent-1",
	"accent-2": "bg-accent-2",
} as const;

/**
 * Конфетти: мелкая геометрия, разбросанная в пустоте.
 *
 * Единственное, что вообще есть на фоне после сноса фактур. Работает ровно потому,
 * что фон пустой: на сетке и шуме эти точки были бы мусором.
 *
 * Декор и только декор — aria-hidden, не ловит курсор, выключается при
 * prefers-reduced-motion.
 */
export function Confetti({
	bits,
	className,
}: { bits: Bit[]; className?: string }) {
	const reduced = useReducedMotion();
	const ref = useRef<HTMLDivElement>(null);
	const { scrollYProgress } = useScroll({
		target: ref,
		offset: ["start end", "end start"],
	});

	return (
		<div
			ref={ref}
			aria-hidden="true"
			className={cn("pointer-events-none absolute inset-0 z-0", className)}
		>
			{bits.map((bit) => (
				<Bit
					key={`${bit.x}-${bit.y}-${bit.shape}`}
					bit={bit}
					progress={scrollYProgress}
					still={Boolean(reduced)}
				/>
			))}
		</div>
	);
}

function Bit({
	bit,
	progress,
	still,
}: {
	bit: Bit;
	progress: ReturnType<typeof useScroll>["scrollYProgress"];
	still: boolean;
}) {
	const y = useSpring(useTransform(progress, [0, 1], [bit.speed, -bit.speed]), {
		stiffness: 70,
		damping: 24,
		mass: 0.8,
	});

	const shape =
		bit.shape === "ring"
			? "rounded-full bg-transparent border-2"
			: bit.shape === "dot"
				? "rounded-full"
				: "";

	const border =
		bit.shape === "ring"
			? bit.tone === "brand"
				? "border-brand"
				: bit.tone === "accent-1"
					? "border-accent-1"
					: "border-accent-2"
			: "";

	return (
		<motion.span
			className={cn(
				"absolute block",
				bit.shape === "ring" ? shape : cn(shape, TONE[bit.tone]),
				border,
			)}
			style={{
				left: `${bit.x}%`,
				top: `${bit.y}%`,
				width: bit.size,
				height: bit.size,
				y: still ? 0 : y,
				rotate: bit.shape === "diamond" ? 45 : 0,
			}}
		/>
	);
}
