import type * as React from "react";

import { cn } from "@/lib/utils";

const TONE = {
	brand: "bg-brand",
	accent1: "bg-accent-1",
	accent2: "bg-accent-2",
	ink: "bg-foreground",
} as const;

/**
 * Цветная плашка, повёрнутая на пару градусов. Внутри — скриншот приложения.
 *
 * Заменила рамку-мокап: скруглённая рамка со свечением, в которой кадр парит по
 * центру, — визитка шаблонного лендинга. Здесь кадр лежит на плоском цветном
 * прямоугольнике, и держит его не рамка, а сам цвет.
 *
 * Поворот идёт `rotate` на обёртке, а не `transform` на кадре: у кадра свой
 * параллакс, а два transform на одном элементе затирают друг друга.
 *
 * ВАЖНО: поворот расширяет ограничивающий прямоугольник — на 375px это готовый
 * источник горизонтальной прокрутки. Поэтому у секции обязан быть overflow-hidden,
 * а гейт verify-page.py проверяет отсутствие горизонтального скролла.
 */
export function Panel({
	children,
	tone = "brand",
	tilt = -3,
	className,
}: {
	children: React.ReactNode;
	tone?: keyof typeof TONE;
	/** Наклон в градусах. Больше 6° — и кадр внутри становится нечитаемым. */
	tilt?: number;
	className?: string;
}) {
	return (
		<div
			className={cn("p-3 sm:p-4", TONE[tone], className)}
			style={{ rotate: `${tilt}deg` }}
		>
			{children}
		</div>
	);
}
