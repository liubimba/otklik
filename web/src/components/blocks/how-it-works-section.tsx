import { ArrowRightIcon, TriangleAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AppShot } from "@/components/ui/app-shot";
import { Badge } from "@/components/ui/badge";
import { Confetti } from "@/components/ui/confetti";
import { Laptop } from "@/components/ui/device";
import { MascotStage } from "@/components/ui/mascot-stage";
import { MascotLaptop } from "@/components/ui/mascots";
import { ParallaxShot } from "@/components/ui/parallax-shot";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { howItWorks } from "@/lib/content";
import { cn } from "@/lib/utils";

type Step = (typeof howItWorks.steps)[number];

/** Автоотклик живёт внутри шага 4, а не отдельной секцией: про него честнее
 *  сказать там же, где речь о проверке письма. */
function AutoApply({
	autoApply,
}: {
	autoApply: NonNullable<Extract<Step, { autoApply: unknown }>["autoApply"]>;
}) {
	return (
		<div className="mt-8 flex flex-col gap-4 border-l-2 border-brand pl-5">
			<h3 className="font-heading text-lg text-balance">{autoApply.title}</h3>
			<p className="text-base text-pretty text-muted-foreground">
				{autoApply.body}
			</p>

			<ol className="flex flex-wrap items-center gap-2">
				{autoApply.pipeline.map((step, index) => (
					<li key={step} className="flex items-center gap-2">
						<Badge variant="outline" className="label-mono py-1.5">
							{step}
						</Badge>
						{index < autoApply.pipeline.length - 1 && (
							<ArrowRightIcon
								className="size-3 text-muted-foreground"
								aria-hidden="true"
							/>
						)}
					</li>
				))}
			</ol>

			<Alert className="px-4 py-3">
				<TriangleAlertIcon />
				<AlertTitle className="font-heading text-base font-extrabold">
					{autoApply.note.title}
				</AlertTitle>
				<AlertDescription className="text-base text-pretty">
					{autoApply.note.body}
				</AlertDescription>
			</Alert>
		</div>
	);
}

/** Плиты позади корпусов чередуют цвет и наклон — чтобы пять шагов подряд не
 *  читались как список. Наклон корпуса держим в пределах ±3°: дальше кадр внутри
 *  начинает читаться хуже, а ноутбук — заваливаться. */
const TONES = ["brand", "accent2", "accent1", "brand", "accent2"] as const;
const TILTS = [-2.5, 2, -1.5, 2.5, -2];

function Step({ step, index }: { step: Step; index: number }) {
	const number = index + 1;
	const flipped = index % 2 === 1;

	return (
		<div
			id={`step-${number}`}
			className={cn(
				"grid scroll-mt-24 items-center gap-10 py-16 md:grid-cols-2 md:gap-16 md:py-24",
				flipped && "md:[&>*:first-child]:order-2",
			)}
		>
			<div>
				{/* Номер шага — гигантской цифрой: он и есть навигация по секции. */}
				<span
					aria-hidden="true"
					className="block font-heading text-7xl leading-none text-brand md:text-8xl"
				>
					{String(number).padStart(2, "0")}
				</span>
				<h3
					id={`step-${number}-title`}
					className="mt-6 max-w-[16ch] font-heading text-3xl text-balance md:text-4xl"
				>
					{step.title}
				</h3>
				<p className="mt-4 max-w-[44ch] text-base text-pretty text-muted-foreground">
					{step.body}
				</p>
				{"autoApply" in step && step.autoApply && (
					<AutoApply autoApply={step.autoApply} />
				)}
			</div>

			<Reveal delay="delay-200">
				{/* Без наклона по курсору: пять наклоняющихся кадров подряд — аттракцион. */}
				<ParallaxShot shift={26} tilt={0}>
					<Laptop tone={TONES[index]} tilt={TILTS[index]}>
						<AppShot
							light={step.shot.light}
							dark={step.shot.dark}
							alt={step.shot.alt}
							placeholder={step.shot.placeholder}
						/>
					</Laptop>
				</ParallaxShot>
			</Reveal>
		</div>
	);
}

export function HowItWorksSection() {
	return (
		<Section
			id="how-it-works"
			backdrop={
				<Confetti
					bits={[
						{ x: 4, y: 8, size: 12, shape: "dot", tone: "accent-1", speed: 50 },
						{
							x: 95,
							y: 30,
							size: 16,
							shape: "diamond",
							tone: "brand",
							speed: 70,
						},
						{
							x: 90,
							y: 72,
							size: 18,
							shape: "ring",
							tone: "accent-2",
							speed: 35,
						},
					]}
				/>
			}
		>
			<SectionHeader
				id="how-it-works"
				eyebrow={howItWorks.eyebrow}
				title={howItWorks.title}
				description={howItWorks.description}
				mascot={
					<MascotStage shape="slab" tone="accent1" tilt={4}>
						<MascotLaptop tone="accent2" />
					</MascotStage>
				}
			/>

			<div className="mt-8">
				{howItWorks.steps.map((step, index) => (
					<Step key={step.title} step={step} index={index} />
				))}
			</div>
		</Section>
	);
}
