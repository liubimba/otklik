import type * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Секция — пустота.
 *
 * Ни фактур, ни подложек, ни свечений: фон одинаков от секции до секции, объекты
 * висят в ней и держатся собственной формой. Раньше здесь чередовались grid/hatch
 * и surface-recessed — вместе с ними ушла и «карточность» страницы.
 *
 * overflow-hidden — не украшение: плашки повёрнуты, а поворот расширяет
 * ограничивающий прямоугольник и на 375px рождает горизонтальную прокрутку.
 */
function Section({
	id,
	className,
	backdrop,
	children,
	...props
}: React.ComponentProps<"section"> & {
	/** Декоративные слои (конфетти). Отдельный слот: контент сидит на z-10. */
	backdrop?: React.ReactNode;
}) {
	return (
		<section
			id={id}
			aria-labelledby={`${id}-title`}
			className={cn(
				"relative scroll-mt-24 overflow-hidden px-4 py-24 md:py-36",
				className,
			)}
			{...props}
		>
			{backdrop}
			<div className="relative z-10 mx-auto flex max-w-container flex-col">
				{children}
			</div>
		</section>
	);
}

/**
 * Заголовок секции: гигантский тип по левому краю, крошечная метка над ним.
 *
 * Эффект даёт не размер, а разрыв — 15px метки рядом со 110px заголовка.
 * Ничего не центрируется: центр на этой странице остался ровно в одном месте,
 * в финальном CTA, и работает он потому, что единственный.
 */
function SectionHeader({
	id,
	eyebrow,
	title,
	description,
	className,
}: {
	id: string;
	eyebrow?: string;
	title: string;
	description?: string;
	className?: string;
}) {
	return (
		<header className={cn("flex flex-col gap-6", className)}>
			{eyebrow && (
				<span className="label-mono label-chip self-start">{eyebrow}</span>
			)}
			<h2 id={`${id}-title`} className="max-w-[14ch] font-heading text-balance">
				{title}
			</h2>
			{description && (
				<p className="max-w-[54ch] text-base text-pretty text-muted-foreground">
					{description}
				</p>
			)}
		</header>
	);
}

export { Section, SectionHeader };
