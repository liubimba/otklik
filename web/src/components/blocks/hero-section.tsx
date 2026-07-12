import { ArrowRightIcon } from "lucide-react";
import type * as React from "react";

import { AppShot } from "@/components/ui/app-shot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Glow } from "@/components/ui/glow";
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
	image: {
		light: string;
		dark: string;
		alt: string;
	};
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
			<div className="mx-auto flex max-w-container flex-col gap-12 pt-16 sm:gap-24">
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
							<Button
								key={action.href}
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
						))}
					</div>

					<div className="relative w-full pt-12">
						<AppShot
							light={image.light}
							dark={image.dark}
							alt={image.alt}
							priority
							className="animate-appear-zoom opacity-0 delay-600"
						/>
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
