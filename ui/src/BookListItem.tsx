import { useEffect } from "react";
import { observer } from "mobx-react-lite";
import BookDetailStore from "./stores/BookDetailStore";

export default observer(function BookListItem({
  title,
  author,
  file,
}: {
  title: string;
  author?: string;
  file: string;
}) {
  return (
    <div>
      <p>
        Title: <span dangerouslySetInnerHTML={{ __html: title }} />
      </p>
      <p>Author: {author || "unknown"}</p>
      <a href={new URL(`books/${file}`, location.href).href}>Download</a>
    </div>
  );
});
