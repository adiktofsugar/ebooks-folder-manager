import { observer } from "mobx-react-lite";
import styles from "./ErrorList.module.css";
import type BookListStore from "./stores/BookListStore";

export default observer(function ErrorList({
	store,
}: { store: BookListStore }) {
	const { errors } = store;
	if (!errors.length) {
		return null;
	}
	return (
		<div className={styles.errorContainer}>
			<h2 className={styles.errorTitle}>Errors while processing</h2>
			<ul className={styles.errorList}>
				{errors.map((e) => {
					return (
						<li key={e.original_filepath} className={styles.errorItem}>
							{e.error_message}
						</li>
					);
				})}
			</ul>
		</div>
	);
});
