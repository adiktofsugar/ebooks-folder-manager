import { observer } from "mobx-react-lite";
import type BookListStore from "./stores/BookListStore";

export default observer(function ErrorList({
	store,
}: { store: BookListStore }) {
	const { errors } = store;
	if (!errors.length) {
		return null;
	}
	return (
		<div>
			<h1>Errors while processing</h1>
			<ul>
				{errors.map((e) => {
					return <li key={e.original_filepath}>{e.error_message}</li>;
				})}
			</ul>
		</div>
	);
});
