"use client";

import {
	motion,
	useMotionValue,
	useReducedMotion,
	useScroll,
	useSpring,
	useTransform,
} from "motion/react";
import type * as React from "react";
import { useRef } from "react";

/**
 * Скриншот приложения, который «живёт»: медленно всплывает при скролле и слегка
 * наклоняется за курсором.
 *
 * Обёртка, а не замена <AppShot>: тот остаётся серверным (тему выбирает CSS, и
 * менять это нельзя — на выборе src в рендере уже горели). Сюда он приходит
 * через children.
 *
 * Наклон живёт на обёртке, а не на самом кадре: на кадре уже висит
 * animate-appear-zoom, и два transform на одном элементе затирают друг друга.
 */
export function ParallaxShot({
	children,
	/** Ход по вертикали, px. Для hero больше, для боковых кадров шагов — меньше. */
	shift = 40,
	/** Максимальный наклон, градусы. 0 — только параллакс, без tilt. */
	tilt = 4,
	className,
}: {
	children: React.ReactNode;
	shift?: number;
	tilt?: number;
	className?: string;
}) {
	const reduced = useReducedMotion();
	const ref = useRef<HTMLDivElement>(null);

	const { scrollYProgress } = useScroll({
		target: ref,
		offset: ["start end", "end start"],
	});
	const y = useSpring(useTransform(scrollYProgress, [0, 1], [shift, -shift]), {
		stiffness: 90,
		damping: 24,
		mass: 0.6,
	});

	const px = useMotionValue(0);
	const py = useMotionValue(0);
	const spring = { stiffness: 120, damping: 18, mass: 0.4 };
	const rotateX = useSpring(
		useTransform(py, [-0.5, 0.5], [tilt, -tilt]),
		spring,
	);
	const rotateY = useSpring(
		useTransform(px, [-0.5, 0.5], [-tilt, tilt]),
		spring,
	);

	// «Меньше движения» — отдаём кадр как есть, без обёртки и без слушателей.
	if (reduced) return <div className={className}>{children}</div>;

	return (
		<motion.div
			ref={ref}
			className={className}
			style={{ y, rotateX, rotateY, transformPerspective: 1200 }}
			onPointerMove={(event) => {
				if (!tilt) return;
				const rect = event.currentTarget.getBoundingClientRect();
				px.set((event.clientX - rect.left) / rect.width - 0.5);
				py.set((event.clientY - rect.top) / rect.height - 0.5);
			}}
			onPointerLeave={() => {
				px.set(0);
				py.set(0);
			}}
		>
			{children}
		</motion.div>
	);
}
