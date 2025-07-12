import { observer } from "mobx-react-lite";
import styles from "./BookListItem.module.css";

export default observer(function BookListItem({
	title,
	author,
	filename,
}: {
	title: string;
	author: string;
	filename: string;
}) {
	return (
		<div className={styles.bookItem}>
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
		</div>
	);
});
