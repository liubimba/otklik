"use client";

import * as React from "react";

/**
 * Reveal-on-scroll.
 *
 * `revealed` начинается с false и на сервере, и на первом клиентском рендере —
 * ничего браузероспецифичного в рендере не читаем, иначе разметка разъедется
 * и React сообщит о hydration mismatch.
 *
 * prefers-reduced-motion здесь сознательно НЕ обрабатывается: за него отвечает
 * CSS (`[data-reveal] { opacity: 1 }` в globals.css). Держать эту логику в двух
 * местах — верный способ их рассинхронить.
 */
export function useReveal<T extends HTMLElement>() {
	const ref = React.useRef<T>(null);
	const [revealed, setRevealed] = React.useState(false);

	React.useEffect(() => {
		const element = ref.current;
		if (!element) return;

		// Страховка: без IntersectionObserver содержимое иначе осталось бы
		// прозрачным навсегда — лучше показать без анимации.
		if (typeof IntersectionObserver === "undefined") {
			const frame = requestAnimationFrame(() => setRevealed(true));
			return () => cancelAnimationFrame(frame);
		}

		const observer = new IntersectionObserver(
			([entry]) => {
				if (entry.isIntersecting) {
					setRevealed(true);
					observer.disconnect();
				}
			},
			{ threshold: 0.15, rootMargin: "0px 0px -10% 0px" },
		);

		observer.observe(element);
		return () => observer.disconnect();
	}, []);

	return { ref, revealed };
}
