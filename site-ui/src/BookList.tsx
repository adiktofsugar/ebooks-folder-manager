import { observer } from "mobx-react-lite";
import { useEffect, useRef, useState } from "react";
import styles from "./BookList.module.css";
import BookListItem from "./BookListItem";
import type BookListStore from "./stores/BookListStore";

export default observer(function BookList({ store }: { store: BookListStore }) {
	const { searchQuery, books } = store;

	return (
		<div>
			<div className={styles.header}>
				<input
					// biome-ignore lint/a11y/noAutofocus: <explanation>
					autoFocus
					type="text"
					placeholder="Search books..."
					value={searchQuery}
					onChange={(e) => store.setSearchQuery(e.target.value)}
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
