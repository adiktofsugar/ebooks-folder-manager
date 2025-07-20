import { observer } from "mobx-react-lite";
import { useState } from "react";
import BookCover from "./BookCover";
import styles from "./BookListItem.module.css";
import type { BookMatchData } from "./interfaces";
import type BookItemStore from "./stores/BookItemStore";

export default observer(function BookListItem({
	book,
	matchData,
}: {
	book: BookItemStore;
	matchData: BookMatchData;
}) {
	const [showMessages, setShowMessages] = useState(false);
	return (
		<div className={styles.bookItem}>
			<div className={styles.bookContent}>
				<h3 className={styles.title}>
					{/* biome-ignore lint/security/noDangerouslySetInnerHtml: fuzzy changes html */}
					<span dangerouslySetInnerHTML={{ __html: matchData.titleHtml }} />
				</h3>
				<p className={styles.author}>
					{/* biome-ignore lint/security/noDangerouslySetInnerHtml: fuzzy changes html */}
					<span dangerouslySetInnerHTML={{ __html: matchData.authorHtml }} />
				</p>
				<a
					href={new URL(book.filename, location.href).href}
					className={styles.downloadLink}
				>
					Download
				</a>
				{book.messages.length > 0 && (
					<div className={styles.messagesSection}>
						<button
							type="button"
							onClick={() => setShowMessages(!showMessages)}
							className={styles.messagesToggle}
						>
							{showMessages ? "Hide" : "Show"} Messages ({book.messages.length})
						</button>
						{showMessages && (
							<div className={styles.messagesList}>
								{book.messages.map((message, index) => (
									// biome-ignore lint/suspicious/noArrayIndexKey: messages are unique log entries
									<div key={index} className={styles.message}>
										{message}
									</div>
								))}
							</div>
						)}
					</div>
				)}
			</div>
			<div className={styles.bookImage}>
				<BookCover
					book={book}
					width={120}
					height={160}
					className={styles.bookCover}
				/>
			</div>
		</div>
	);
});
