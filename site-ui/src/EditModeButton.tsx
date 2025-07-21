import { observer } from "mobx-react-lite";
import { useEffect, useState } from "react";
import styles from "./EditModeButton.module.css";
import EditModeInfo from "./EditModeInfo";
import type DbStore from "./stores/DbStore";

export default observer(function EditModeButton({ store }: { store: DbStore }) {
	const [showInfo, setShowInfo] = useState(false);
	const handleClick = () => {
		setShowInfo(!showInfo);
	};

	const { meta } = store;
	if (!meta?.edit_api_url) {
		// we're not in edit mode
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
					<EditModeInfo meta={meta} />
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
