import { TriangleAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { risks } from "@/lib/content";
import { sectionIcons } from "@/lib/icons";

const DELAYS = ["delay-100", "delay-200", "delay-300"] as const;

export function RisksSection() {
	return (
		<Section id="risks">
			<SectionHeader
				id="risks"
				eyebrow={risks.eyebrow}
				title={risks.title}
				description={risks.description}
			/>

			{/* destructive-токены, а не brand: brand тоже красный, они бы слиплись. */}
			<Reveal delay="delay-100" className="mt-12">
				<Alert
					variant="destructive"
					className="border-destructive/30 bg-destructive/5 px-5 py-4"
				>
					<TriangleAlertIcon />
					<AlertTitle className="font-heading text-lg font-semibold">
						{risks.warning.title}
					</AlertTitle>
					<AlertDescription className="text-base text-pretty">
						{risks.warning.body}
					</AlertDescription>
				</Alert>
			</Reveal>

			<h3 className="mt-16 font-heading text-xl text-balance">
				{risks.mitigationsTitle}
			</h3>

			<div className="mt-6 grid gap-4 md:grid-cols-3">
				{risks.mitigations.map((item, index) => {
					const Icon = sectionIcons[item.icon];

					return (
						<Reveal key={item.title} delay={DELAYS[index % DELAYS.length]}>
							<Card className="h-full">
								<CardHeader className="gap-3">
									<Icon className="size-5 text-brand" aria-hidden="true" />
									<h4 className="font-heading text-base text-balance">
										{item.title}
									</h4>
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
