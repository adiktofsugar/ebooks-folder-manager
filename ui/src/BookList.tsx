import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import BookListStore from "./stores/BookListStore";
import BookListItem from "./BookListItem";

export default observer(function BookList() {
  const [bookListStore] = useState(() => new BookListStore());
  useEffect(() => {
    bookListStore.load();
  }, [bookListStore]);
  const { error, pending, booksLoadProgress, books, searchQuery } =
    bookListStore;
  if (error) {
    return <div>Error: {error}</div>;
  }
  if (pending) {
    return <div>Loading...</div>;
  }
  if (booksLoadProgress < 1) {
    return <div>Loading books... {Math.round(booksLoadProgress * 100)}%</div>;
  }
  if (!books) {
    return <div>No books available, or, more likely, something went wrong</div>;
  }

  return (
    <div>
      <div>
        <input
          type="text"
          placeholder="Search books..."
          value={searchQuery}
          onChange={(e) => bookListStore.setSearchQuery(e.target.value)}
        />
      </div>
      <ul>
        {books.map(({ title, file, author }, i) => (
          <li key={i}>
            <BookListItem title={title} file={file} author={author} />
          </li>
        ))}
      </ul>
    </div>
  );
});
