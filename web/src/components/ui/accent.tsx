"use client";

import {
	motion,
	useReducedMotion,
	useScroll,
	useSpring,
	useTransform,
} from "motion/react";
import type * as React from "react";
import { useRef } from "react";

import { cn } from "@/lib/utils";

/**
 * Акцентный объект: декоративная фигура у края секции, всплывающая при скролле.
 *
 * Декор и только декор — `aria-hidden`, `pointer-events: none`. Если объект несёт
 * смысл, он не должен жить здесь: скринридер его не увидит.
 *
 * Ход параллакса задаётся на объект: разные скорости у соседних фигур — это и есть
 * ощущение глубины. Одинаковые превращают набор в наклейку.
 */
export function Accent({
	children,
	className,
	speed = 40,
	spin = 0,
}: {
	children: React.ReactNode;
	/** Позиция и размер — таргет-классы Tailwind (top/left/size). */
	className?: string;
	/** Ход по вертикали, px: положительный — объект отстаёт от страницы. */
	speed?: number;
	/** Наклон, градусы. Лёгкая «небрежность» — чтобы не выглядело печатью. */
	spin?: number;
}) {
	const reduced = useReducedMotion();
	const ref = useRef<HTMLDivElement>(null);

	const { scrollYProgress } = useScroll({
		target: ref,
		offset: ["start end", "end start"],
	});
	const y = useSpring(useTransform(scrollYProgress, [0, 1], [speed, -speed]), {
		stiffness: 80,
		damping: 26,
		mass: 0.7,
	});

	const base = cn("pointer-events-none absolute z-0 text-brand", className);

	if (reduced) {
		return (
			<div
				ref={ref}
				aria-hidden="true"
				className={base}
				style={{ rotate: `${spin}deg` }}
			>
				{children}
			</div>
		);
	}

	return (
		<motion.div
			ref={ref}
			aria-hidden="true"
			className={base}
			style={{ y, rotate: spin }}
		>
			{children}
		</motion.div>
	);
}
