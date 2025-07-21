import type { DragEvent, FormEvent } from "react";
import { useRef, useState } from "react";
import type BookItemStore from "./stores/BookItemStore";
import { useBookListStore } from "./stores/BookListStore";

interface BookCoverProps {
	book: BookItemStore;
	width: number;
	height: number;
	className?: string;
}

export default function BookCover({
	book,
	width,
	height,
	className,
}: BookCoverProps) {
	const store = useBookListStore();
	// Cover images are generated server-side and stored as {hash}.png
	const coverUrl = `books/${book.hash}.png`;

	return (
		<div>
			<img
				src={coverUrl}
				alt="Book cover"
				width={width}
				height={height}
				className={className}
				style={{ objectFit: "cover" }}
			/>
			{store.isEditMode ? <BookCoverEditForm book={book} /> : null}
		</div>
	);
}

function BookCoverEditForm({ book }: { book: BookItemStore }) {
	const store = useBookListStore();
	const [selectedFile, setSelectedFile] = useState<File | null>(null);
	const [isDragging, setIsDragging] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	// TODO: add a way for this to hit the edit api and generate a list of covers, then select one
	function handleSubmit(e: FormEvent) {
		e.preventDefault();
		if (!selectedFile) return;

		const formData = new FormData();
		formData.append("image", selectedFile);
		formData.append("book_filepath", book.original_filepath);

		fetch(new URL("/upload-cover-image", store.editApiUrl), {
			method: "POST",
			body: formData,
		});
	}

	function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
		const file = e.target.files?.[0];
		if (file?.type.startsWith("image/")) {
			setSelectedFile(file);
		}
	}

	function handleDrop(e: DragEvent<HTMLDivElement>) {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);

		const file = e.dataTransfer.files[0];
		if (file?.type.startsWith("image/")) {
			setSelectedFile(file);
			if (fileInputRef.current) {
				const dataTransfer = new DataTransfer();
				dataTransfer.items.add(file);
				fileInputRef.current.files = dataTransfer.files;
			}
		}
	}

	function handleDragOver(e: DragEvent<HTMLDivElement>) {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(true);
	}

	function handleDragLeave(e: DragEvent<HTMLDivElement>) {
		e.preventDefault();
		e.stopPropagation();
		setIsDragging(false);
	}

	return (
		<form onSubmit={handleSubmit}>
			<div
				onDrop={handleDrop}
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				style={{
					border: isDragging ? "2px dashed #007bff" : "2px dashed #ccc",
					borderRadius: "4px",
					padding: "10px",
					textAlign: "center",
					backgroundColor: isDragging ? "#f0f8ff" : "transparent",
					transition: "all 0.2s ease",
				}}
			>
				<input
					ref={fileInputRef}
					type="file"
					accept="image/*"
					onChange={handleFileChange}
					style={{ marginBottom: "8px" }}
				/>
				<p style={{ margin: "8px 0", fontSize: "14px", color: "#666" }}>
					or drag and drop an image here
				</p>
				{selectedFile && (
					<p style={{ margin: "8px 0", fontSize: "14px", color: "#333" }}>
						Selected: {selectedFile.name}
					</p>
				)}
			</div>
			<button
				type="submit"
				disabled={!selectedFile}
				style={{ marginTop: "8px" }}
			>
				Upload
			</button>
		</form>
	);
}
