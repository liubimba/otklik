import type * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Общая рамка секции. overflow-hidden здесь — самая дешёвая страховка от
 * горизонтального скролла на 375px, который легко устраивают свечения и блюры.
 */
function Section({
	id,
	variant = "default",
	className,
	children,
	...props
}: React.ComponentProps<"section"> & { variant?: "default" | "muted" }) {
	return (
		<section
			id={id}
			aria-labelledby={`${id}-title`}
			className={cn(
				"relative scroll-mt-24 overflow-hidden px-4 py-16 sm:py-24 md:py-32",
				"bg-noise",
				variant === "muted" ? "surface-recessed" : "bg-background bg-grid",
				className,
			)}
			{...props}
		>
			<div className="mx-auto flex max-w-container flex-col">{children}</div>
		</section>
	);
}

/**
 * Заголовок секции. Сознательно без градиента: bg-clip-text остаётся
 * привилегией <h1> в hero, иначе визуальная иерархия страницы рассыпается.
 */
function SectionHeader({
	id,
	eyebrow,
	title,
	description,
	align = "center",
	className,
}: {
	id: string;
	eyebrow?: string;
	title: string;
	description?: string;
	align?: "center" | "start";
	className?: string;
}) {
	return (
		<div
			className={cn(
				"flex flex-col gap-4",
				align === "center" ? "items-center text-center" : "items-start",
				className,
			)}
		>
			{eyebrow && <span className="label-mono text-brand">{eyebrow}</span>}
			<h2 id={`${id}-title`} className="font-heading text-balance">
				{title}
			</h2>
			{description && (
				<p
					className={cn(
						"max-w-[620px] text-base text-pretty text-muted-foreground sm:text-lg",
						align === "center" && "mx-auto",
					)}
				>
					{description}
				</p>
			)}
		</div>
	);
}

export { Section, SectionHeader };
