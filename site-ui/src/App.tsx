import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import styles from "./App.module.css";
import BookList from "./BookList";
import ErrorList from "./ErrorList";
import ThemeToggle from "./ThemeToggle";
import DbStore from "./stores/DbStore";
import ThemeStore from "./stores/ThemeStore";

export default observer(function App() {
	const [store] = useState(() => new DbStore());
	const [theme] = useState(() => new ThemeStore());
	useEffect(() => {
		store.load();
	}, [store]);
	const { error, pending, bookStore } = store;

	useEffect(() => {
		const root = document.documentElement;
		if (theme.dark) {
			root.classList.add("dark");
		} else {
			root.classList.remove("dark");
		}
	}, [theme.dark]);

	if (error) {
		return <div className={styles.error}>Error: {error}</div>;
	}
	if (pending) {
		return <div className={styles.loading}>Loading your ebook library...</div>;
	}
	if (!bookStore) {
		return (
			<div className={styles.error}>
				No books available, or, more likely, something went wrong
			</div>
		);
	}
	return (
		<>
			<ThemeToggle store={theme} />
			<div>
				<h1 className={styles.title}>Ebook Library</h1>
				<ErrorList store={bookStore} />
				<BookList store={bookStore} />
			</div>
		</>
	);
});
