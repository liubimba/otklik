import { ArrowRightIcon } from "lucide-react";
import type * as React from "react";

import { Accent } from "@/components/ui/accent";
import { AppShot, type Shot } from "@/components/ui/app-shot";
import { Backdrop } from "@/components/ui/backdrop";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Etch } from "@/components/ui/etch";
import { Glow } from "@/components/ui/glow";
import { Magnetic } from "@/components/ui/magnetic";
import { ParallaxShot } from "@/components/ui/parallax-shot";
import { cn } from "@/lib/utils";

interface HeroAction {
	text: string;
	href: string;
	icon?: React.ReactNode;
	variant?: "default" | "glow";
}

interface HeroProps {
	badge?: {
		text: string;
		action: {
			text: string;
			href: string;
		};
	};
	title: string;
	description: string;
	actions: HeroAction[];
	image: Shot;
}

export function HeroSection({
	badge,
	title,
	description,
	actions,
	image,
}: HeroProps) {
	return (
		<section
			className={cn(
				"relative bg-background text-foreground texture-grid texture-noise",
				"px-4 py-12 sm:py-24 md:py-32",
				"fade-bottom overflow-hidden pb-0",
			)}
		>
			<Backdrop aurora beams />

			{/* Гравюры — по полям, в верхней зоне: ниже начинается кадр приложения,
			    и объект под ним всё равно не было бы видно. Разные скорости параллакса
			    у соседних фигур — это и есть глубина; одинаковые превратили бы набор
			    в наклейку. Прячем до lg: на узком экране полей просто нет. */}
			<Accent className="top-20 left-[3%] hidden lg:block" speed={52} spin={-7}>
				<Etch name="letter" width={170} className="opacity-30" />
			</Accent>
			<Accent className="top-28 right-[3%] hidden lg:block" speed={34} spin={5}>
				<Etch name="typewriter" width={140} className="opacity-25" />
			</Accent>
			<Accent
				className="top-[42%] left-[4%] hidden xl:block"
				speed={74}
				spin={4}
			>
				<Etch name="quill-hand" width={140} className="opacity-25" />
			</Accent>

			{/* z-10 на всей колонке, а не только на заголовке: Backdrop — позиционированный
			    слой с z-0, и без этого он накрыл бы бейдж, который лежит в обычном потоке. */}
			<div className="relative z-10 mx-auto flex max-w-container flex-col gap-12 pt-16 sm:gap-24">
				<div className="flex flex-col items-center gap-6 text-center sm:gap-12">
					{badge && (
						<Badge
							variant="outline"
							className="animate-enter-up opacity-0 gap-2 py-1"
						>
							<span className="text-muted-foreground">{badge.text}</span>
							<a
								href={badge.action.href}
								className="flex items-center gap-1 rounded-sm underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							>
								{badge.action.text}
								<ArrowRightIcon className="size-3" aria-hidden="true" />
							</a>
						</Badge>
					)}

					<h1 className="relative z-10 inline-block animate-enter-clip opacity-0 delay-100 bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text font-heading text-balance text-transparent drop-shadow-2xl">
						{title}
					</h1>

					<p className="relative z-10 max-w-[550px] animate-enter-up text-base font-medium text-pretty text-muted-foreground opacity-0 delay-300 sm:text-xl">
						{description}
					</p>

					<div className="relative z-10 flex animate-enter-up flex-wrap justify-center gap-4 opacity-0 delay-400">
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

					<div className="relative w-full pt-12">
						<ParallaxShot shift={48} tilt={4}>
							<AppShot
								light={image.light}
								dark={image.dark}
								alt={image.alt}
								placeholder={image.placeholder}
								priority
								// Hero занимает всю колонку, а не половину, как кадры шагов.
								sizes="(max-width: 768px) 100vw, (max-width: 1280px) 92vw, 1200px"
								className="animate-appear-zoom opacity-0 delay-600"
							/>
						</ParallaxShot>
						<Glow
							variant="top"
							className="animate-appear-zoom opacity-0 delay-1000"
						/>
					</div>
				</div>
			</div>
		</section>
	);
}
