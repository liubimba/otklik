import type * as React from "react";

import { cn } from "@/lib/utils";

const TONE = {
	brand: "bg-brand",
	accent1: "bg-accent-1",
	accent2: "bg-accent-2",
} as const;

/**
 * Сцена под маскота: цветная фигура, белая клякса, тень, конфетти.
 *
 * На референсе характер персонажам даёт не рисунок, а постановка: герой стоит на
 * жёлтом круге или на повёрнутой цветной плите, за ним расплывается белое пятно,
 * под ним лежит тень, вокруг летит мелочь. Без этого та же фигура читается как
 * наклейка, приклеенная к пустому фону.
 *
 * Главное здесь — маскот НАМЕРЕННО вылезает за край фигуры: голова и ступни
 * выходят наружу. Впиши его целиком внутрь круга — и получится аватарка в
 * кружочке; вылезающий силуэт делает из него персонажа, который в кадре не
 * помещается.
 */
export function MascotStage({
	children,
	shape = "circle",
	tone = "accent2",
	tilt = 0,
	className,
}: {
	children: React.ReactNode;
	shape?: "circle" | "slab";
	tone?: keyof typeof TONE;
	/** Наклон плиты. Круг не наклоняем — поворот круга не виден. */
	tilt?: number;
	className?: string;
}) {
	return (
		<div className={cn("relative", className)}>
			{/* Цветная фигура. Заметно меньше маскота по высоте — за этим и стоит:
			    из неё торчат голова и ноги.
			    overflow-hidden обязателен: клякса лежит ВНУТРИ фигуры и обрезается по
			    её краю. Без обрезки она вылезает наружу, и круг выглядит откушенным. */}
			<div
				aria-hidden="true"
				className={cn(
					"absolute inset-x-[2%] top-[14%] bottom-[10%] overflow-hidden",
					TONE[tone],
					shape === "circle" ? "rounded-full" : "rounded-none",
				)}
				style={shape === "slab" ? { rotate: `${tilt}deg` } : undefined}
			>
				{/* Клякса — единственная органическая форма на всей странице: она и
				    даёт персонажу «землю под ногами». Красится фоном, поэтому в тёмной
				    теме тёмная, в светлой светлая — и в обеих читается на цвете. */}
				<svg
					aria-hidden="true"
					focusable="false"
					viewBox="0 0 100 100"
					className="absolute inset-0 size-full text-background"
					preserveAspectRatio="none"
				>
					<path
						fill="currentColor"
						d="M12 74c-6-9 2-16 10-14s10 8 19 6 12-10 22-9 17 8 25 4v39H8c-1-8 8-17 4-26Z"
					/>
				</svg>
			</div>

			{/* Тень: маскот стоит, а не висит. */}
			<div
				aria-hidden="true"
				className="absolute bottom-[6%] left-1/2 h-[3%] w-[46%] -translate-x-1/2 rounded-[50%] bg-foreground/20"
			/>

			{/* Мелочь вокруг — та же геометрия, что в конфетти страницы. Статичная:
			    у маскота она держит композицию, а не привлекает внимание. */}
			<span
				aria-hidden="true"
				className="absolute top-[6%] left-[4%] size-2 rounded-full bg-accent-1"
			/>
			<span
				aria-hidden="true"
				className="absolute top-[20%] right-0 size-3 rotate-45 bg-brand"
			/>
			<span
				aria-hidden="true"
				className="absolute bottom-[16%] left-0 size-2.5 rotate-45 bg-accent-2"
			/>

			<div className="relative z-10">{children}</div>
		</div>
	);
}
