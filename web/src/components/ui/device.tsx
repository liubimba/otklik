import type * as React from "react";

import { cn } from "@/lib/utils";

const TONE = {
	brand: "bg-brand",
	accent1: "bg-accent-1",
	accent2: "bg-accent-2",
	none: "hidden",
} as const;

/**
 * Скриншот в корпусе ноутбука.
 *
 * Пришёл на смену цветной плашке с равномерным полем вокруг кадра: такая плашка
 * ничего не изображает — это просто рамка, и читается она как дешёвая обводка.
 * Корпус же объясняет, что перед нами: Otklik — десктопное приложение, и кадр
 * должен стоять на столе, а не висеть в цветном паспарту.
 *
 * Цвет никуда не делся, он ушёл ЗА устройство отдельной плитой — как зелёная
 * плита под телефонами на референсе. Плита живёт своей формой и своим наклоном,
 * а не повторяет контур кадра.
 *
 * Корпус графитовый в обеих темах намеренно: серебристая крышка на белом фоне
 * растворяется, а настоящее приложение тёмное. Тени и блик — единственное место
 * на странице, где мы отступаем от плоскости; здесь это и есть смысл — объём.
 *
 * ВАЖНО: наклон расширяет ограничивающий прямоугольник, на 375px это готовый
 * источник горизонтальной прокрутки. У секции обязан быть overflow-hidden;
 * verify-page.py сторожит, что полосы прокрутки не появилось.
 */
export function Laptop({
	children,
	tone = "brand",
	tilt = -2,
	className,
}: {
	children: React.ReactNode;
	tone?: keyof typeof TONE;
	/** Наклон корпуса в градусах. Больше 4° — и кадр внутри становится нечитаемым. */
	tilt?: number;
	className?: string;
}) {
	return (
		<div className={cn("relative", className)}>
			{/* Цветная плита позади — подиум, на котором стоит ноутбук.
			    Шире корпуса и наклонена в другую сторону: будь она уже и соосна,
			    из-под днища торчал бы цветной подтёк, а по бокам — снова обводка. */}
			<div
				aria-hidden="true"
				className={cn(
					"absolute -inset-x-[5%] top-[16%] -bottom-[7%] rounded-[1.5rem]",
					TONE[tone],
				)}
				style={{ rotate: `${-tilt * 1.4}deg` }}
			/>

			{/* z-10 не украшение: обёртка параллакса — motion.div с transform, и
			    порядок наложения внутри неё наружу не виден. Кадр обязан быть
			    выше плиты по слою, а не по надежде. */}
			<div className="relative z-10" style={{ rotate: `${tilt}deg` }}>
				{/* Крышка. Верхнее поле шире боковых — там сидит камера, как у настоящего. */}
				<div className="relative rounded-t-[10px] bg-linear-to-b from-[#4a4e55] to-[#2c2f34] p-[5px] pt-[11px] pb-0 shadow-[0_28px_60px_-24px_rgb(0_0_0/0.55)] ring-1 ring-black/25 sm:rounded-t-[16px] sm:p-[8px] sm:pt-[17px] dark:shadow-[0_28px_70px_-24px_rgb(0_0_0/0.8)]">
					{/* Блик по верхней кромке: одна светлая линия делает металл металлом. */}
					<span
						aria-hidden="true"
						className="pointer-events-none absolute inset-x-[10%] top-0 h-px bg-white/25"
					/>
					<span
						aria-hidden="true"
						className="absolute top-[4px] left-1/2 size-[3px] -translate-x-1/2 rounded-full bg-white/30 ring-1 ring-black/40 sm:top-[6px] sm:size-[5px]"
					/>

					<div className="overflow-hidden rounded-[3px] bg-black sm:rounded-[5px]">
						{children}
					</div>
				</div>

				{/* Петля и основание: чуть шире крышки, иначе ноутбук читается как монитор. */}
				<div className="relative -mx-[2.5%] h-[9px] rounded-b-[6px] bg-linear-to-b from-[#3a3e44] via-[#2c2f34] to-[#17191c] shadow-[0_18px_30px_-18px_rgb(0_0_0/0.6)] sm:h-[14px] sm:rounded-b-[10px]">
					<span
						aria-hidden="true"
						className="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/12"
					/>
					{/* Выемка под палец. */}
					<span
						aria-hidden="true"
						className="absolute top-0 left-1/2 h-[3px] w-[14%] -translate-x-1/2 rounded-b-full bg-black/35 sm:h-[5px]"
					/>
				</div>
			</div>
		</div>
	);
}
