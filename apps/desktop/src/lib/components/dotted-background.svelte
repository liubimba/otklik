<script lang="ts">
import { onMount } from "svelte";

const { dark = false }: { dark?: boolean } = $props();

let canvas: HTMLCanvasElement;
let dotColor = "oklch(0.922 0 0)";

function readDotColor() {
	const c = getComputedStyle(document.documentElement)
		.getPropertyValue("--border")
		.trim();
	if (c) dotColor = c;
}

onMount(() => {
	const context = canvas.getContext("2d");
	if (context === null) return;
	const ctx: CanvasRenderingContext2D = context;

	const SPACING = 18;
	const DOT = 1.1;
	const RADIUS = 190;
	const R2 = RADIUS * RADIUS;
	const PULL = 64;

	const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
	const dpr = Math.min(window.devicePixelRatio || 1, 2);

	let width = 0;
	let height = 0;
	let targetX = -9999;
	let targetY = -9999;
	let curX = -9999;
	let curY = -9999;
	let intensity = 0;
	let targetIntensity = 0;
	let raf = 0;
	let running = false;

	function start() {
		if (running) return;
		running = true;
		raf = requestAnimationFrame(frame);
	}

	function resize() {
		const r = canvas.getBoundingClientRect();
		width = r.width;
		height = r.height;
		canvas.width = Math.round(width * dpr);
		canvas.height = Math.round(height * dpr);
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		start();
	}

	function onMove(e: MouseEvent) {
		const r = canvas.getBoundingClientRect();
		const nx = e.clientX - r.left;
		const ny = e.clientY - r.top;
		if (curX < -9000) {
			curX = nx;
			curY = ny;
		}
		targetX = nx;
		targetY = ny;
		targetIntensity =
			nx >= 0 && ny >= 0 && nx <= r.width && ny <= r.height ? 1 : 0;
		start();
	}

	function onLeave() {
		targetIntensity = 0;
		start();
	}

	function frame() {
		curX += (targetX - curX) * 0.16;
		curY += (targetY - curY) * 0.16;
		intensity += (targetIntensity - intensity) * 0.09;

		ctx.clearRect(0, 0, width, height);
		ctx.fillStyle = dotColor;

		const active = !reduced && intensity > 0.01;
		const pull = PULL * intensity;

		for (let gx = SPACING / 2; gx < width; gx += SPACING) {
			for (let gy = SPACING / 2; gy < height; gy += SPACING) {
				let px = gx;
				let py = gy;
				let r = DOT;
				if (active) {
					const dx = curX - gx;
					const dy = curY - gy;
					const d2 = dx * dx + dy * dy;
					if (d2 < R2) {
						const dist = Math.sqrt(d2) || 0.0001;
						const f = 1 - dist / RADIUS;
						const ff = f * f;
						const move = Math.min(pull * ff, dist);
						px = gx + (dx / dist) * move;
						py = gy + (dy / dist) * move;
						r = DOT * (1 + ff);
					}
				}
				ctx.beginPath();
				ctx.arc(px, py, r, 0, Math.PI * 2);
				ctx.fill();
			}
		}

		const moving =
			!reduced &&
			(intensity > 0.003 ||
				targetIntensity > 0.003 ||
				Math.abs(curX - targetX) > 0.5 ||
				Math.abs(curY - targetY) > 0.5);
		if (moving) {
			raf = requestAnimationFrame(frame);
		} else {
			running = false;
		}
	}

	readDotColor();
	resize();
	const ro = new ResizeObserver(resize);
	ro.observe(canvas);
	window.addEventListener("mousemove", onMove);
	document.addEventListener("mouseleave", onLeave);

	return () => {
		cancelAnimationFrame(raf);
		ro.disconnect();
		window.removeEventListener("mousemove", onMove);
		document.removeEventListener("mouseleave", onLeave);
	};
});

$effect(() => {
	dark;
	requestAnimationFrame(readDotColor);
});
</script>

<canvas
	bind:this={canvas}
	class="pointer-events-none absolute inset-0 size-full"
	aria-hidden="true"
></canvas>
