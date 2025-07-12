import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import styles from "./App.module.css";
import BookList from "./BookList";
import ErrorList from "./ErrorList";
import ThemeToggle from "./ThemeToggle";
import { ThemeProvider } from "./contexts/ThemeContext";
import BookListStore from "./stores/BookListStore";

function AppContent() {
	const [store] = useState(() => new BookListStore());
	useEffect(() => {
		store.load();
	}, [store]);
	const { error, pending, books } = store;
	if (error) {
		return <div className={styles.error}>Error: {error}</div>;
	}
	if (pending) {
		return <div className={styles.loading}>Loading your ebook library...</div>;
	}
	if (!books) {
		return (
			<div className={styles.error}>
				No books available, or, more likely, something went wrong
			</div>
		);
	}
	return (
		<>
			<ThemeToggle />
			<div className={styles.container}>
				<h1 className={styles.title}>Ebook Library</h1>
				<ErrorList store={store} />
				<BookList store={store} />
			</div>
		</>
	);
}

export default observer(function App() {
	return (
		<ThemeProvider>
			<AppContent />
		</ThemeProvider>
	);
});
