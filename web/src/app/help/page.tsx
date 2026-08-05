import type { Metadata } from "next";
import Link from "next/link";

import { SiteFooter } from "@/components/blocks/site-footer";
import { ThemeToggle } from "@/components/theme-toggle";
import { Laptop } from "@/components/ui/device";
import { ParallaxShot } from "@/components/ui/parallax-shot";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { VideoLightbox } from "@/components/ui/video-lightbox";
import { usageHelp } from "@/lib/content";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
	title: "Как пользоваться? — Otklik",
	description:
		"Как пользоваться Otklik: настройка резюме и модели, генерация письма, отправка отклика и авто-отправка.",
};

const TONES = ["brand", "accent2", "accent1", "brand", "accent2"] as const;
const TILTS = [-2.5, 2, -1.5, 2.5, -2];

type Block = (typeof usageHelp.blocks)[number];

function HelpBlock({ block, index }: { block: Block; index: number }) {
	const number = index + 1;
	const flipped = index % 2 === 1;

	return (
		<div
			className={cn(
				"grid scroll-mt-24 items-center gap-10 py-16 md:grid-cols-2 md:gap-16 md:py-24",
				flipped && "md:[&>*:first-child]:order-2",
			)}
		>
			<div>
				<span
					aria-hidden="true"
					className="block font-heading text-7xl leading-none text-brand md:text-8xl"
				>
					{String(number).padStart(2, "0")}
				</span>
				<h2 className="mt-6 max-w-[16ch] font-heading text-3xl text-balance md:text-4xl">
					{block.title}
				</h2>
				<p className="mt-4 max-w-[44ch] text-base text-pretty text-muted-foreground">
					{block.body}
				</p>
			</div>

			<Reveal delay="delay-200">
				<ParallaxShot shift={26} tilt={0}>
					<Laptop tone={TONES[index]} tilt={TILTS[index]}>
						<VideoLightbox src={block.clip} alt={block.alt} />
					</Laptop>
				</ParallaxShot>
			</Reveal>
		</div>
	);
}

export default function HelpPage() {
	return (
		<>
			<main className="flex-1">
				<header className="mx-auto flex max-w-container items-center justify-between px-4 pt-4">
					<Link
						href="/"
						className="font-heading text-lg font-extrabold tracking-tight"
					>
						Otklik
					</Link>
					<ThemeToggle />
				</header>

				<Section id="help">
					<SectionHeader
						id="help"
						eyebrow={usageHelp.eyebrow}
						title={usageHelp.title}
						description={usageHelp.description}
					/>

					<div className="mt-8">
						{usageHelp.blocks.map((block, index) => (
							<HelpBlock key={block.title} block={block} index={index} />
						))}
					</div>
				</Section>
			</main>

			<SiteFooter />
		</>
	);
}
