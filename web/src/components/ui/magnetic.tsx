"use client";

import {
	motion,
	useMotionValue,
	useReducedMotion,
	useSpring,
} from "motion/react";
import type * as React from "react";

/**
 * Кнопка слегка тянется к курсору. Микровзаимодействие ровно на двух главных
 * действиях страницы — «Скачать» и «Исходный код»; развесить его на всё подряд
 * значит обесценить.
 *
 * Смещение маленькое (6px по умолчанию): цель — ощущение отклика, а не игрушка.
 * Больше 8px и кнопка начинает убегать от курсора, по ней становится труднее
 * попасть — это уже вредит.
 */
export function Magnetic({
	children,
	strength = 6,
}: {
	children: React.ReactNode;
	strength?: number;
}) {
	const reduced = useReducedMotion();
	const x = useMotionValue(0);
	const y = useMotionValue(0);
	const spring = { stiffness: 200, damping: 15, mass: 0.3 };
	const sx = useSpring(x, spring);
	const sy = useSpring(y, spring);

	if (reduced) return <>{children}</>;

	return (
		<motion.div
			className="inline-flex"
			style={{ x: sx, y: sy }}
			onPointerMove={(event) => {
				const rect = event.currentTarget.getBoundingClientRect();
				const dx = event.clientX - (rect.left + rect.width / 2);
				const dy = event.clientY - (rect.top + rect.height / 2);
				x.set((dx / (rect.width / 2)) * strength);
				y.set((dy / (rect.height / 2)) * strength);
			}}
			onPointerLeave={() => {
				x.set(0);
				y.set(0);
			}}
		>
			{children}
		</motion.div>
	);
}
