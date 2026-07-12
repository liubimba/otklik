import { type VariantProps, cva } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

const glowVariants = cva("pointer-events-none absolute w-full", {
	variants: {
		variant: {
			top: "top-0",
			above: "-top-[128px]",
			bottom: "bottom-0",
			below: "-bottom-[128px]",
			center: "top-[50%]",
		},
	},
	defaultVariants: {
		variant: "top",
	},
});

function Glow({
	className,
	variant,
	...props
}: React.ComponentProps<"div"> & VariantProps<typeof glowVariants>) {
	return (
		<div
			data-slot="glow"
			aria-hidden="true"
			className={cn(glowVariants({ variant }), className)}
			{...props}
		>
			<div
				className={cn(
					"absolute left-1/2 h-[256px] w-[60%] -translate-x-1/2 scale-[2.5] rounded-[50%] bg-[radial-gradient(ellipse_at_center,_color-mix(in_oklab,var(--brand-foreground)_50%,transparent)_10%,_transparent_60%)] sm:h-[512px]",
					variant === "center" && "-translate-y-1/2",
				)}
			/>
			<div
				className={cn(
					"absolute left-1/2 h-[128px] w-[40%] -translate-x-1/2 scale-[2] rounded-[50%] bg-[radial-gradient(ellipse_at_center,_color-mix(in_oklab,var(--brand)_30%,transparent)_10%,_transparent_60%)] sm:h-[256px]",
					variant === "center" && "-translate-y-1/2",
				)}
			/>
		</div>
	);
}

export { Glow, glowVariants };
