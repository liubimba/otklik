"use client";

import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "@/components/ui/accordion";
import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { pricing } from "@/lib/content";

export function PricingFaqSection() {
	return (
		<Section id="pricing" variant="muted">
			<SectionHeader
				id="pricing"
				eyebrow={pricing.eyebrow}
				title={pricing.title}
				description={pricing.description}
			/>

			<Reveal delay="delay-200" className="mt-14 w-full md:mt-20">
				<Accordion
					type="single"
					collapsible
					className="mx-auto w-full max-w-[720px]"
				>
					{pricing.faq.map((item) => (
						<AccordionItem key={item.q} value={item.q}>
							{/* py-4 — иначе строка аккордеона не дотягивает до 44px по высоте касания */}
							<AccordionTrigger className="py-4 text-left font-heading text-base font-extrabold">
								{item.q}
							</AccordionTrigger>
							<AccordionContent className="text-base text-pretty text-muted-foreground">
								{item.a}
							</AccordionContent>
						</AccordionItem>
					))}
				</Accordion>
			</Reveal>
		</Section>
	);
}
