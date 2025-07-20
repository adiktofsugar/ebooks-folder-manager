import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import styles from "./EditModeButton.module.css";
import type EditDbStore from "./stores/EditDbStore";
import EditModeInfo from "./EditModeInfo";

export default observer(function EditModeButton({
	store,
}: { store: EditDbStore }) {
	const [showInfo, setShowInfo] = useState(false);
	const handleClick = () => {
		setShowInfo(!showInfo);
	};

	useEffect(() => {
		store.load();
	}, [store]);

	const { error, pending, api } = store;
	if (error) {
		return <pre>{error}</pre>;
	}

	return (
		<>
			<button
				type="button"
				onClick={handleClick}
				className={styles.toggle}
				disabled={pending}
			>
				{pending ? "..." : "edit server active"}
			</button>
			{showInfo && api && (
				<EditModeInfo
					store={api.info}
					onClose={() => {
						setShowInfo(false);
					}}
				/>
			)}
		</>
	);
});
