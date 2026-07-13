"use client";

import {
	motion,
	useMotionValue,
	useReducedMotion,
	useSpring,
} from "motion/react";
import { useEffect, useRef } from "react";

/**
 * Пятно света, следующее за курсором внутри родительской секции.
 *
 * Двигается через `transform`, а не пересчётом `background: radial-gradient(… at X Y)`:
 * градиент пришлось бы перерисовывать каждый кадр на всю площадь секции, а translate
 * уходит на GPU. Координаты живут в MotionValue — React при движении мыши не
 * ререндерится ни разу.
 *
 * Слушатель висит на РОДИТЕЛЕ, а не на самом слое: слой обязан быть
 * `pointer-events: none` (иначе он перехватит клики по контенту), а такой элемент
 * событий указателя не получает вовсе. Родитель обязан быть `relative`.
 */
export function Spotlight({ size = 34 }: { size?: number }) {
	const reduced = useReducedMotion();
	const ref = useRef<HTMLDivElement>(null);

	const x = useMotionValue(0);
	const y = useMotionValue(0);
	const opacity = useMotionValue(0);
	const spring = { stiffness: 140, damping: 22, mass: 0.5 };
	const sx = useSpring(x, spring);
	const sy = useSpring(y, spring);
	const sOpacity = useSpring(opacity, { stiffness: 60, damping: 20 });

	useEffect(() => {
		const host = ref.current?.parentElement;
		if (!host || reduced) return;

		// Тонкая мышь = мышь. На тач-устройстве курсора нет, а pointermove там
		// приходит от пальца — пятно бы дёргалось под тапами.
		const fine = window.matchMedia("(pointer: fine)");
		if (!fine.matches) return;

		const move = (event: PointerEvent) => {
			const rect = host.getBoundingClientRect();
			x.set(event.clientX - rect.left);
			y.set(event.clientY - rect.top);
		};
		const enter = () => opacity.set(1);
		const leave = () => opacity.set(0);

		host.addEventListener("pointermove", move);
		host.addEventListener("pointerenter", enter);
		host.addEventListener("pointerleave", leave);
		return () => {
			host.removeEventListener("pointermove", move);
			host.removeEventListener("pointerenter", enter);
			host.removeEventListener("pointerleave", leave);
		};
	}, [reduced, x, y, opacity]);

	// «Меньше движения» — не приглушить, а убрать: пятно существует только ради
	// движения, статичным оно превращается в случайную кляксу.
	if (reduced) return null;

	return (
		<div
			ref={ref}
			aria-hidden="true"
			// Потолок яркости — на обёртке, а не в MotionValue: тему в рендере читать
			// нельзя (гидратация не перепишет разошедшийся атрибут), а CSS знает её сам.
			// Прозрачности перемножаются: 1.0 из пружины × 0.2 здесь.
			className="pointer-events-none absolute inset-0 z-0 overflow-hidden opacity-20 dark:opacity-45"
		>
			<motion.div
				style={{
					x: sx,
					y: sy,
					opacity: sOpacity,
					width: `${size}rem`,
					height: `${size}rem`,
					marginLeft: `-${size / 2}rem`,
					marginTop: `-${size / 2}rem`,
					background:
						"radial-gradient(closest-side, color-mix(in oklab, var(--brand) 70%, transparent), transparent)",
				}}
				className="absolute top-0 left-0 rounded-full blur-3xl"
			/>
		</div>
	);
}
