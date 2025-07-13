import { observer } from "mobx-react-lite";
import { useState } from "react";
import BookCover from "./BookCover";
import styles from "./BookListItem.module.css";

export default observer(function BookListItem({
	title,
	author,
	filename,
	hash,
	messages,
}: {
	title: string;
	author: string;
	filename: string;
	hash: string;
	messages: string[];
}) {
	const [showMessages, setShowMessages] = useState(false);
	return (
		<div className={styles.bookItem}>
			<div className={styles.bookContent}>
				<h3 className={styles.title}>
					{/* biome-ignore lint/security/noDangerouslySetInnerHtml: fuzzy changes html */}
					<span dangerouslySetInnerHTML={{ __html: title }} />
				</h3>
				<p className={styles.author}>
					{/* biome-ignore lint/security/noDangerouslySetInnerHtml: fuzzy changes html */}
					<span dangerouslySetInnerHTML={{ __html: author }} />
				</p>
				<a
					href={new URL(filename, location.href).href}
					className={styles.downloadLink}
				>
					Download
				</a>
				{messages.length > 0 && (
					<div className={styles.messagesSection}>
						<button
							type="button"
							onClick={() => setShowMessages(!showMessages)}
							className={styles.messagesToggle}
						>
							{showMessages ? "Hide" : "Show"} Messages ({messages.length})
						</button>
						{showMessages && (
							<div className={styles.messagesList}>
								{messages.map((message, index) => (
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
					hash={hash}
					width={120}
					height={160}
					className={styles.bookCover}
				/>
			</div>
		</div>
	);
});
