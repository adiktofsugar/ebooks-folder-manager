import { useEffect, useRef } from "react";

interface BookCoverProps {
	hash: string;
	width: number;
	height: number;
	className?: string;
}

export default function BookCover({
	hash,
	width,
	height,
	className,
}: BookCoverProps) {
	const canvasRef = useRef<HTMLCanvasElement>(null);

	useEffect(() => {
		const canvas = canvasRef.current;
		if (!canvas) return;

		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		// Generate deterministic values from hash
		const hashToNumber = (str: string, index: number) => {
			let num = 0;
			for (let i = 0; i < str.length; i++) {
				num = (num * 31 + str.charCodeAt((i + index) % str.length)) % 1000000;
			}
			return num / 1000000;
		};

		// Choose pattern type
		const patternType = Math.floor(hashToNumber(hash, 0) * 6);

		// Clear canvas
		ctx.fillStyle = "#ffffff";
		ctx.fillRect(0, 0, width, height);

		switch (patternType) {
			case 0:
				drawGeometricPattern(ctx, hash, width, height, hashToNumber);
				break;
			case 1:
				drawColorBlocks(ctx, hash, width, height, hashToNumber);
				break;
			case 2:
				drawIdenticon(ctx, hash, width, height, hashToNumber);
				break;
			case 3:
				drawWavePattern(ctx, hash, width, height, hashToNumber);
				break;
			case 4:
				drawCircuitPattern(ctx, hash, width, height, hashToNumber);
				break;
			default:
				drawAbstractShapes(ctx, hash, width, height, hashToNumber);
		}

		// Add subtle border
		ctx.strokeStyle = "#cccccc";
		ctx.lineWidth = 1;
		ctx.strokeRect(0, 0, width, height);
	}, [hash, width, height]);

	return (
		<canvas
			ref={canvasRef}
			width={width}
			height={height}
			className={className}
		/>
	);
}

function drawGeometricPattern(
	ctx: CanvasRenderingContext2D,
	hash: string,
	width: number,
	height: number,
	hashToNumber: (str: string, index: number) => number,
) {
	const hue = hashToNumber(hash, 10) * 360;
	const columns = Math.floor(hashToNumber(hash, 20) * 4) + 3;
	const rows = Math.floor(hashToNumber(hash, 30) * 5) + 4;
	const cellWidth = width / columns;
	const cellHeight = height / rows;

	for (let i = 0; i < columns; i++) {
		for (let j = 0; j < rows; j++) {
			const filled = hashToNumber(hash, i * rows + j) > 0.5;
			if (filled) {
				const lightness = 50 + hashToNumber(hash, i * rows + j + 100) * 30;
				ctx.fillStyle = `hsl(${hue}, 70%, ${lightness}%)`;
				ctx.fillRect(i * cellWidth, j * cellHeight, cellWidth, cellHeight);
			}
		}
	}
}

function drawColorBlocks(
	ctx: CanvasRenderingContext2D,
	hash: string,
	width: number,
	height: number,
	hashToNumber: (str: string, index: number) => number,
) {
	const baseHue = hashToNumber(hash, 10) * 360;
	const blockCount = Math.floor(hashToNumber(hash, 20) * 3) + 2;
	const isVertical = hashToNumber(hash, 30) > 0.5;

	for (let i = 0; i < blockCount; i++) {
		const hue = (baseHue + i * 60) % 360;
		const saturation = 40 + hashToNumber(hash, 40 + i) * 40;
		const lightness = 40 + hashToNumber(hash, 50 + i) * 40;
		ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;

		if (isVertical) {
			const blockHeight = height / blockCount;
			ctx.fillRect(0, i * blockHeight, width, blockHeight);
		} else {
			const blockWidth = width / blockCount;
			ctx.fillRect(i * blockWidth, 0, blockWidth, height);
		}
	}
}

function drawIdenticon(
	ctx: CanvasRenderingContext2D,
	hash: string,
	width: number,
	height: number,
	hashToNumber: (str: string, index: number) => number,
) {
	const hue = hashToNumber(hash, 10) * 360;
	const gridSize = 5;
	const cellWidth = width / gridSize;
	const cellHeight = height / gridSize;

	// Create symmetric pattern
	const pattern: boolean[][] = [];
	for (let y = 0; y < gridSize; y++) {
		pattern[y] = [];
		for (let x = 0; x < Math.ceil(gridSize / 2); x++) {
			pattern[y][x] = hashToNumber(hash, y * gridSize + x) > 0.5;
		}
		// Mirror the pattern
		for (let x = Math.ceil(gridSize / 2); x < gridSize; x++) {
			pattern[y][x] = pattern[y][gridSize - 1 - x];
		}
	}

	// Draw pattern
	for (let y = 0; y < gridSize; y++) {
		for (let x = 0; x < gridSize; x++) {
			if (pattern[y][x]) {
				ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
				ctx.fillRect(x * cellWidth, y * cellHeight, cellWidth, cellHeight);
			}
		}
	}
}

function drawWavePattern(
	ctx: CanvasRenderingContext2D,
	hash: string,
	width: number,
	height: number,
	hashToNumber: (str: string, index: number) => number,
) {
	const hue1 = hashToNumber(hash, 10) * 360;
	const hue2 = hashToNumber(hash, 20) * 360;
	const waveCount = Math.floor(hashToNumber(hash, 30) * 5) + 3;
	const amplitude = height / 4;
	const frequency = hashToNumber(hash, 40) * 0.05 + 0.02;

	ctx.lineWidth = 2;

	for (let i = 0; i < waveCount; i++) {
		const progress = i / (waveCount - 1);
		const hue = hue1 + (hue2 - hue1) * progress;
		const yOffset = (height / (waveCount + 1)) * (i + 1);
		const phase = hashToNumber(hash, 50 + i) * Math.PI * 2;

		ctx.strokeStyle = `hsl(${hue}, 70%, 50%)`;
		ctx.beginPath();
		for (let x = 0; x <= width; x++) {
			const y = yOffset + Math.sin(x * frequency + phase) * amplitude;
			if (x === 0) {
				ctx.moveTo(x, y);
			} else {
				ctx.lineTo(x, y);
			}
		}
		ctx.stroke();
	}
}

function drawCircuitPattern(
	ctx: CanvasRenderingContext2D,
	hash: string,
	width: number,
	height: number,
	hashToNumber: (str: string, index: number) => number,
) {
	const hue = hashToNumber(hash, 10) * 360;
	const nodeCount = Math.floor(hashToNumber(hash, 20) * 8) + 5;

	ctx.strokeStyle = `hsl(${hue}, 70%, 40%)`;
	ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
	ctx.lineWidth = 2;

	// Draw connections
	const nodes: { x: number; y: number }[] = [];
	for (let i = 0; i < nodeCount; i++) {
		const x = hashToNumber(hash, 30 + i * 2) * width;
		const y = hashToNumber(hash, 31 + i * 2) * height;
		nodes.push({ x, y });
	}

	// Draw lines between nodes
	for (let i = 0; i < nodes.length; i++) {
		const connections = Math.floor(hashToNumber(hash, 100 + i) * 3) + 1;
		for (let j = 0; j < connections; j++) {
			const targetIndex = Math.floor(
				hashToNumber(hash, 200 + i * 10 + j) * nodes.length,
			);
			if (targetIndex !== i) {
				ctx.beginPath();
				ctx.moveTo(nodes[i].x, nodes[i].y);
				ctx.lineTo(nodes[targetIndex].x, nodes[targetIndex].y);
				ctx.stroke();
			}
		}
	}

	// Draw nodes
	for (const node of nodes) {
		ctx.beginPath();
		ctx.arc(node.x, node.y, 4, 0, Math.PI * 2);
		ctx.fill();
	}
}

function drawAbstractShapes(
	ctx: CanvasRenderingContext2D,
	hash: string,
	width: number,
	height: number,
	hashToNumber: (str: string, index: number) => number,
) {
	const shapeCount = Math.floor(hashToNumber(hash, 10) * 6) + 4;
	const baseHue = hashToNumber(hash, 20) * 360;

	for (let i = 0; i < shapeCount; i++) {
		const shapeType = Math.floor(hashToNumber(hash, 30 + i) * 3);
		const x = hashToNumber(hash, 100 + i * 2) * width;
		const y = hashToNumber(hash, 101 + i * 2) * height;
		const size =
			hashToNumber(hash, 200 + i) * Math.min(width, height) * 0.3 + 10;
		const rotation = hashToNumber(hash, 300 + i) * Math.PI * 2;
		const hue = (baseHue + i * 30) % 360;

		ctx.save();
		ctx.translate(x, y);
		ctx.rotate(rotation);

		ctx.fillStyle = `hsla(${hue}, 70%, 50%, 0.7)`;
		ctx.strokeStyle = `hsl(${hue}, 70%, 30%)`;
		ctx.lineWidth = 2;

		ctx.beginPath();
		if (shapeType === 0) {
			// Circle
			ctx.arc(0, 0, size / 2, 0, Math.PI * 2);
		} else if (shapeType === 1) {
			// Square
			ctx.rect(-size / 2, -size / 2, size, size);
		} else {
			// Triangle
			ctx.moveTo(0, -size / 2);
			ctx.lineTo(-size / 2, size / 2);
			ctx.lineTo(size / 2, size / 2);
			ctx.closePath();
		}
		ctx.fill();
		ctx.stroke();

		ctx.restore();
	}
}
