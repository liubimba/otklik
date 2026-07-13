import { ArrowRightIcon, TriangleAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AppShot } from "@/components/ui/app-shot";
import { Badge } from "@/components/ui/badge";
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
		<div className="mt-8 flex flex-col gap-4 border-l-2 border-brand/30 pl-5">
			<h3 className="font-heading text-lg text-balance">{autoApply.title}</h3>
			<p className="text-base text-pretty text-muted-foreground">
				{autoApply.body}
			</p>

			<ol className="flex flex-wrap items-center gap-x-2 gap-y-2">
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

function StepSection({ step, index }: { step: Step; index: number }) {
	const number = index + 1;
	const flipped = index % 2 === 1;

	return (
		<Section id={`step-${number}`} variant={flipped ? "muted" : "default"}>
			<div
				className={cn(
					"grid items-center gap-10 lg:grid-cols-2 lg:gap-16",
					// Змейка: у чётных шагов скриншот уезжает влево. Порядок в разметке
					// не меняем — на мобильном текст всегда должен идти первым.
					flipped && "lg:[&>*:first-child]:order-2",
				)}
			>
				<div>
					<SectionHeader
						id={`step-${number}`}
						align="start"
						eyebrow={`Шаг ${String(number).padStart(2, "0")}`}
						title={step.title}
						description={step.body}
					/>
					{"autoApply" in step && step.autoApply && (
						<AutoApply autoApply={step.autoApply} />
					)}
				</div>

				<Reveal delay="delay-200">
					<AppShot
						light={step.shot.light}
						dark={step.shot.dark}
						alt={step.shot.alt}
						placeholder={step.shot.placeholder}
					/>
				</Reveal>
			</div>
		</Section>
	);
}

export function HowItWorksSection() {
	return (
		<>
			<Section id="how-it-works" className="pb-0 md:pb-0">
				<SectionHeader
					id="how-it-works"
					eyebrow={howItWorks.eyebrow}
					title={howItWorks.title}
					description={howItWorks.description}
				/>
			</Section>

			{howItWorks.steps.map((step, index) => (
				<StepSection key={step.title} step={step} index={index} />
			))}
		</>
	);
}
