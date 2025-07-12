import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import BookList from "./BookList";
import ErrorList from "./ErrorList";
import BookListStore from "./stores/BookListStore";

export default observer(function App() {
	const [store] = useState(() => new BookListStore());
	useEffect(() => {
		store.load();
	}, [store]);
	const { error, pending, books } = store;
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
			<ErrorList store={store} />
			<BookList store={store} />
		</div>
	);
});
