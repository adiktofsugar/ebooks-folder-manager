import { observer } from "mobx-react-lite";
import { useEffect, useRef, useState } from "react";
import styles from "./BookList.module.css";
import BookListItem from "./BookListItem";
import BookListStore from "./stores/BookListStore";

export default observer(function BookList() {
	const [bookListStore] = useState(() => new BookListStore());
	useEffect(() => {
		bookListStore.load();
	}, [bookListStore]);
	const { error, pending, books, searchQuery } = bookListStore;
	if (error) {
		return <div>Error: {error}</div>;
	}
	if (pending) {
		return <div>Loading...</div>;
	}
	if (!books) {
		return <div>No books available, or, more likely, something went wrong</div>;
	}

	return (
		<div>
			<div className={styles.header}>
				<input
					// biome-ignore lint/a11y/noAutofocus: <explanation>
					autoFocus
					type="text"
					placeholder="Search books..."
					value={searchQuery}
					onChange={(e) => bookListStore.setSearchQuery(e.target.value)}
				/>
			</div>
			<ul>
				{books.map(({ title, filename, author }) => (
					<li key={filename}>
						<BookListItem title={title} filename={filename} author={author} />
					</li>
				))}
			</ul>
		</div>
	);
});
