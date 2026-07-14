import type * as React from "react";

import { AppShot, type Shot } from "@/components/ui/app-shot";
import { Button } from "@/components/ui/button";
import { Confetti } from "@/components/ui/confetti";
import { Laptop } from "@/components/ui/device";
import { Magnetic } from "@/components/ui/magnetic";
import { ParallaxShot } from "@/components/ui/parallax-shot";

interface HeroAction {
	text: string;
	href: string;
	icon?: React.ReactNode;
	variant?: "default" | "glow";
}

interface HeroProps {
	kicker: string;
	title: string;
	description: string;
	actions: HeroAction[];
	image: Shot;
}

/**
 * Hero: гигантский тип в пустоте.
 *
 * Заголовок занимает половину экрана, а текст рядом с ним — 15px. Работает именно
 * разрыв, а не размер: одинаково крупные заголовок и лид дали бы просто «большой
 * шрифт», а не акцент.
 *
 * Ушли три визитки шаблонного лендинга: бейдж-пилюля со стрелкой, градиентный
 * заголовок через bg-clip-text и свечение под кадром. Кадр приложения больше не
 * парит по центру в рамке — он лежит на плоской цветной плашке, повёрнутой на пару
 * градусов, и упирается в правый край экрана.
 */
export function HeroSection({
	kicker,
	title,
	description,
	actions,
	image,
}: HeroProps) {
	return (
		<section className="relative overflow-hidden bg-background px-4 pt-10 pb-24 text-foreground sm:pt-16 md:pb-32">
			<Confetti
				bits={[
					{ x: 6, y: 18, size: 14, shape: "dot", tone: "accent-1", speed: 60 },
					{
						x: 88,
						y: 12,
						size: 18,
						shape: "diamond",
						tone: "accent-2",
						speed: 40,
					},
					{ x: 92, y: 44, size: 10, shape: "dot", tone: "brand", speed: 80 },
					{
						x: 14,
						y: 52,
						size: 22,
						shape: "ring",
						tone: "accent-2",
						speed: 30,
					},
					{ x: 70, y: 6, size: 12, shape: "diamond", tone: "brand", speed: 70 },
				]}
			/>

			<div className="relative z-10 mx-auto max-w-container">
				<p className="label-mono flex items-center gap-3 text-brand">
					<span className="h-px w-8 bg-brand" aria-hidden="true" />
					{kicker}
				</p>

				{/* Заголовок намеренно шире колонки текста: он и есть картинка. */}
				<h1 className="mt-8 max-w-[13ch] font-heading text-balance">{title}</h1>

				<div className="mt-10 flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
					<p className="max-w-[46ch] text-base text-pretty text-muted-foreground">
						{description}
					</p>

					<div className="flex flex-wrap gap-4">
						{actions.map((action) => (
							<Magnetic key={action.href}>
								<Button
									variant={action.variant}
									size="lg"
									asChild
									className="h-11 rounded-lg px-6 text-base"
								>
									<a href={action.href} className="flex items-center gap-2">
										{action.icon}
										{action.text}
									</a>
								</Button>
							</Magnetic>
						))}
					</div>
				</div>
			</div>

			{/* Плашка держит левую ось заголовка и упирается в правый край окна. */}
			<div className="relative z-10 mt-20 pl-4 sm:pl-[max(1rem,calc((100vw-80rem)/2))]">
				<ParallaxShot shift={40} tilt={0} className="relative z-10 origin-left">
					<Laptop tone="brand" tilt={-2}>
						<AppShot
							light={image.light}
							dark={image.dark}
							alt={image.alt}
							placeholder={image.placeholder}
							priority
							sizes="(max-width: 768px) 100vw, 90vw"
							className="animate-appear-zoom opacity-0 delay-600"
						/>
					</Laptop>
				</ParallaxShot>
			</div>
		</section>
	);
}
