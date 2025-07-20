import { observer } from "mobx-react-lite";
import EditModeButton from "./EditModeButton";
import ThemeToggle from "./ThemeToggle";
import styles from "./TopControls.module.css";
import type EditDbStore from "./stores/EditDbStore";
import type ThemeStore from "./stores/ThemeStore";

interface TopControlsProps {
	themeStore: ThemeStore;
	editStore: EditDbStore;
}

export default observer(function TopControls({
	themeStore,
	editStore,
}: TopControlsProps) {
	return (
		<div className={styles.container}>
			<EditModeButton store={editStore} />
			<ThemeToggle store={themeStore} />
		</div>
	);
});
