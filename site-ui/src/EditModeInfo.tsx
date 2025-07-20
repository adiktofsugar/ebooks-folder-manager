import { observer } from "mobx-react-lite";
import { useEffect } from "react";
import styles from "./EditModeInfo.module.css";
import type EditApiInfoStore from "./stores/EditApiInfoStore";

export default observer(function EditModeInfo({
	store,
}: { store: EditApiInfoStore }) {
	useEffect(() => {
		store.load();
	}, [store]);

	const { error, pending, data } = store;

	if (error) {
		return <p>{error}</p>;
	}
	if (pending) {
		return <p>Loading...</p>;
	}
	if (!data) {
		return <p>No data</p>;
	}
	return (
		<>
			<h3 className={styles.infoTitle}>Edit Server Info</h3>
			<pre className={styles.infoPre}>{JSON.stringify(data, null, 2)}</pre>
		</>
	);
});
