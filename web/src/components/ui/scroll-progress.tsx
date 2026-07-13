"use client";

import { motion, useReducedMotion, useScroll, useSpring } from "motion/react";

/**
 * Полоса прогресса чтения. Единственный элемент, который держит связь между
 * длинной страницей и тем, сколько её осталось.
 *
 * scaleX, а не width: width — это layout на каждый кадр скролла, scaleX уходит
 * на композитор.
 */
export function ScrollProgress() {
	const reduced = useReducedMotion();
	const { scrollYProgress } = useScroll();
	const scaleX = useSpring(scrollYProgress, {
		stiffness: 120,
		damping: 30,
		restDelta: 0.001,
	});

	// При «меньше движения» полоса не исчезает — она информативна, а не декоративна.
	// Просто перестаёт пружинить.
	return (
		<motion.div
			aria-hidden="true"
			style={{ scaleX: reduced ? scrollYProgress : scaleX }}
			className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-brand"
		/>
	);
}
