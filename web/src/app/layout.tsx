import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import "./globals.css";

import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({
	variable: "--font-body",
	subsets: ["latin", "cyrillic"],
});

const manrope = Manrope({
	variable: "--font-display",
	subsets: ["latin", "cyrillic"],
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
			className={`${inter.variable} ${manrope.variable} h-full antialiased`}
		>
			<head>
				{/* Reveal-обёртки стартуют прозрачными и проявляются скриптом.
            Без JS страница осталась бы пустой — возвращаем видимость. */}
				<noscript>
					<style>
						{"[data-reveal],[data-typed] span{opacity:1 !important}"}
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
					{children}
				</ThemeProvider>
			</body>
		</html>
	);
}
