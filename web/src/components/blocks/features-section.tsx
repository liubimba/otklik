import { LetterFlow } from "@/components/blocks/letter-flow";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { features } from "@/lib/content";
import { sectionIcons } from "@/lib/icons";

const DELAYS = ["delay-100", "delay-200", "delay-300"] as const;

export function FeaturesSection() {
	return (
		<Section id="features" variant="muted">
			<SectionHeader
				id="features"
				eyebrow={features.eyebrow}
				title={features.title}
				description={features.description}
			/>

			{/* Схема раскрывает заголовок секции: видно, что каждая фраза письма
			    выросла из резюме и описания вакансии, а не выдумана. */}
			<LetterFlow />

			<div className="mt-14 grid gap-4 md:grid-cols-2">
				{features.items.map((item, index) => {
					const Icon = sectionIcons[item.icon];

					return (
						<Reveal key={item.title} delay={DELAYS[index % DELAYS.length]}>
							<Card className="h-full">
								<CardHeader className="gap-3">
									<Icon className="size-5 text-brand" aria-hidden="true" />
									<h3 className="font-heading text-lg font-semibold text-balance">
										{item.title}
									</h3>
								</CardHeader>
								<CardContent>
									<p className="text-base text-pretty text-muted-foreground">
										{item.body}
									</p>
								</CardContent>
							</Card>
						</Reveal>
					);
				})}
			</div>
		</Section>
	);
}
