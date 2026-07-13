import { Reveal } from "@/components/ui/reveal";
import { Section, SectionHeader } from "@/components/ui/section";
import { pricing } from "@/lib/content";

const DELAYS = ["delay-100", "delay-200", "delay-300"] as const;

/**
 * FAQ прозой в две колонки, без аккордеона: шесть коротких ответов за кликом —
 * это шесть кликов ради полстраницы текста. Заодно секция стала серверной.
 */
export function PricingFaqSection() {
	return (
		<Section id="pricing">
			<SectionHeader
				id="pricing"
				eyebrow={pricing.eyebrow}
				title={pricing.title}
				description={pricing.description}
			/>

			<dl className="mt-14 grid gap-x-16 gap-y-10 md:grid-cols-2">
				{pricing.faq.map((item, index) => (
					<Reveal key={item.q} delay={DELAYS[index % DELAYS.length]}>
						<dt className="font-heading text-base font-extrabold text-balance">
							{item.q}
						</dt>
						<dd className="mt-2 max-w-[52ch] text-base text-pretty text-muted-foreground">
							{item.a}
						</dd>
					</Reveal>
				))}
			</dl>
		</Section>
	);
}
