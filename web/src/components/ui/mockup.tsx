import { type VariantProps, cva } from "class-variance-authority";
import type * as React from "react";

import { cn } from "@/lib/utils";

const mockupVariants = cva(
	"relative z-10 flex overflow-hidden border border-border/5 border-t-border/15 shadow-2xl",
	{
		variants: {
			type: {
				mobile: "max-w-[350px] rounded-[48px]",
				responsive: "w-full rounded-md md:rounded-xl",
				window: "w-full rounded-md",
			},
		},
		defaultVariants: {
			type: "responsive",
		},
	},
);

function Mockup({
	className,
	type,
	...props
}: React.ComponentProps<"div"> & VariantProps<typeof mockupVariants>) {
	return (
		<div
			data-slot="mockup"
			className={cn(mockupVariants({ type }), className)}
			{...props}
		/>
	);
}

const mockupFrameVariants = cva(
	"relative z-10 flex overflow-hidden rounded-2xl bg-accent/5 backdrop-blur-sm",
	{
		variants: {
			size: {
				small: "p-2",
				large: "p-4",
			},
		},
		defaultVariants: {
			size: "small",
		},
	},
);

function MockupFrame({
	className,
	size,
	...props
}: React.ComponentProps<"div"> & VariantProps<typeof mockupFrameVariants>) {
	return (
		<div
			data-slot="mockup-frame"
			className={cn(mockupFrameVariants({ size }), className)}
			{...props}
		/>
	);
}

export { Mockup, MockupFrame, mockupVariants, mockupFrameVariants };
