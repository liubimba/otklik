import type { Metadata } from "next";
import { Geologica, Golos_Text, JetBrains_Mono } from "next/font/google";
import "./globals.css";

import { ThemeProvider } from "@/components/theme-provider";
import { ScrollProgress } from "@/components/ui/scroll-progress";

const display = Geologica({
	variable: "--font-display",
	subsets: ["latin", "cyrillic"],
	weight: ["400", "800"],
});

const body = Golos_Text({
	variable: "--font-body",
	subsets: ["latin", "cyrillic"],
	weight: ["400", "500"],
});

const mono = JetBrains_Mono({
	variable: "--font-mono",
	subsets: ["latin", "cyrillic"],
	weight: ["400", "500"],
});

export const metadata: Metadata = {
	title: "Otklik — отклики на вакансии без рутины",
	description:
		"Десктопное приложение: находит вакансии на hh.ru, пишет сопроводительное письмо под каждую и отправляет отклик за вас.",
};

export default function RootLayout({
	children,
}: Readonly<{
	children: React.ReactNode;
}>) {
	return (
		<html
			lang="ru"
			suppressHydrationWarning
			className={`${display.variable} ${body.variable} ${mono.variable} h-full antialiased`}
		>
			<head>
				{/* Reveal-обёртки стартуют прозрачными и проявляются скриптом.
            Без JS страница осталась бы пустой — возвращаем видимость. */}
				<noscript>
					<style>
						{
							"[data-reveal],[data-typed] span,.animate-enter-up,.animate-enter-clip{opacity:1 !important}"
						}
					</style>
				</noscript>
			</head>
			<body className="flex min-h-full flex-col">
				<ThemeProvider
					attribute="class"
					defaultTheme="dark"
					enableSystem
					disableTransitionOnChange
				>
					<ScrollProgress />
					{children}
				</ThemeProvider>
			</body>
		</html>
	);
}
