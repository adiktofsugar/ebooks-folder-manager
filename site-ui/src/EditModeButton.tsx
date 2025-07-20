import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import styles from "./EditModeButton.module.css";
import EditModeInfo from "./EditModeInfo";
import type EditDbStore from "./stores/EditDbStore";

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

	const { error, pending, data, api } = store;
	if (error) {
		return <pre>{error}</pre>;
	}

	if (pending) {
		// it only loads once
		return null;
	}

	if (!api) {
		return null;
	}

	return (
		<div className={styles.container}>
			<button type="button" onClick={handleClick} className={styles.toggle}>
				edit server active
			</button>
			{showInfo && (
				<EditModeInfoContainer
					onClose={() => {
						setShowInfo(false);
					}}
				>
					<EditModeInfo store={api.info} />
				</EditModeInfoContainer>
			)}
		</div>
	);
});

function EditModeInfoContainer({
	children,
	onClose,
}: {
	children: React.ReactNode;
	onClose: () => unknown;
}) {
	return (
		<div className={styles.infoPanel}>
			{children}
			<button
				type="button"
				onClick={() => onClose()}
				className={styles.infoCloseButton}
			>
				Close
			</button>
		</div>
	);
}
