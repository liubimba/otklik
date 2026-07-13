import type * as React from "react";

/**
 * Рукописный овал вокруг фразы — как красная обводка вокруг почты на референсе.
 *
 * Овал нарочно незамкнут и неровен: замкнутый эллипс читается как рамка UI,
 * а не как пометка живой рукой. Именно эта небрежность и есть смысл приёма —
 * единственный «человеческий» жест на странице, собранной машиной.
 *
 * Обводка лежит ПОД текстом (`-z-10`) и не ловит курсор.
 */
export function Scribble({ children }: { children: React.ReactNode }) {
	return (
		<span className="scribble-host">
			<svg
				aria-hidden="true"
				viewBox="0 0 200 60"
				preserveAspectRatio="none"
				className="pointer-events-none absolute -inset-x-3 -inset-y-2 -z-10 h-[calc(100%+1rem)] w-[calc(100%+1.5rem)] text-brand"
			>
				<path
					d="M22 14C60 2 148 0 182 12c14 6 16 22 4 32-22 18-118 20-158 8C12 48 6 32 18 20c8-8 30-14 58-16"
					fill="none"
					stroke="currentColor"
					strokeWidth="3"
					strokeLinecap="round"
				/>
			</svg>
			{children}
		</span>
	);
}
