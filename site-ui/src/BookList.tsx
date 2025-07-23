import { observer } from "mobx-react-lite";
import styles from "./BookList.module.css";
import BookListItem from "./BookListItem";
import type BookListStore from "./stores/BookListStore";
import { BookListStoreContext } from "./stores/BookListStore";

export default observer(function BookList({ store }: { store: BookListStore }) {
	const { searchQuery, booksSorted } = store;

	return (
		<BookListStoreContext.Provider value={store}>
			<div>
				<div className={styles.header}>
					<input
						// biome-ignore lint/a11y/noAutofocus: <explanation>
						autoFocus
						type="text"
						placeholder="Search books..."
						value={searchQuery}
						onChange={(e) => store.setSearchQuery(e.target.value)}
						className={styles.searchInput}
					/>
				</div>
				<ul className={styles.bookList}>
					{booksSorted.map(({ book, matchData }) => (
						<li key={book.hash}>
							<BookListItem book={book} matchData={matchData} />
						</li>
					))}
				</ul>
			</div>
		</BookListStoreContext.Provider>
	);
});
