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
	// Cover images are now generated server-side and stored as {hash}.png
	const coverUrl = `books/${hash}.png`;

	return (
		<img
			src={coverUrl}
			alt="Book cover"
			width={width}
			height={height}
			className={className}
			style={{ objectFit: "cover" }}
		/>
	);
}
