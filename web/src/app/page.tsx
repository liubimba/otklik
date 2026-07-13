import { DownloadIcon } from "lucide-react";

import { CtaSection } from "@/components/blocks/cta-section";
import { FeaturesSection } from "@/components/blocks/features-section";
import { HeroSection } from "@/components/blocks/hero-section";
import { HowItWorksSection } from "@/components/blocks/how-it-works-section";
import { PricingFaqSection } from "@/components/blocks/pricing-faq-section";
import { PrivacySection } from "@/components/blocks/privacy-section";
import { RisksSection } from "@/components/blocks/risks-section";
import { SiteFooter } from "@/components/blocks/site-footer";
import { ThemeToggle } from "@/components/theme-toggle";
import { Icons } from "@/components/ui/icons";
import { links } from "@/lib/links";

export default function Home() {
	return (
		<>
			<main className="flex-1">
				<header className="mx-auto flex max-w-container items-center justify-between px-4 pt-4">
					<span className="font-heading text-lg font-extrabold tracking-tight">
						Otklik
					</span>
					<ThemeToggle />
				</header>

				<HeroSection
					badge={{
						text: "Отклики на hh.ru — на автопилоте",
						action: {
							text: "Как это работает",
							href: "#how-it-works",
						},
					}}
					title="Откликайтесь на вакансии, не тратя на это вечера"
					description="Otklik находит подходящие вакансии на hh.ru и пишет сопроводительное письмо под каждую. Вы читаете письмо и нажимаете «Откликнуться» — отклик уходит с вашего аккаунта."
					actions={[
						{
							text: "Скачать приложение",
							href: links.releases,
							variant: "default",
							icon: <DownloadIcon className="size-5" aria-hidden="true" />,
						},
						{
							text: "Исходный код",
							href: links.github,
							variant: "glow",
							icon: <Icons.gitHub className="size-5" aria-hidden="true" />,
						},
					]}
					image={{
						light: "/app-light.png",
						dark: "/app-dark.png",
						placeholder: {
							light: "/app-light.svg",
							dark: "/app-dark.svg",
						},
						alt: "Экран Otklik: очередь вакансий и сгенерированное сопроводительное письмо",
					}}
				/>

				<HowItWorksSection />
				<FeaturesSection />
				<PrivacySection />
				<RisksSection />
				<PricingFaqSection />
				<CtaSection />
			</main>

			<SiteFooter />
		</>
	);
}
