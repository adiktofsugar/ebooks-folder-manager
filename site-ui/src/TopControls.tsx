import { observer } from "mobx-react-lite";
import EditModeButton from "./EditModeButton";
import ThemeToggle from "./ThemeToggle";
import styles from "./TopControls.module.css";
import type DbStore from "./stores/DbStore";
import type ThemeStore from "./stores/ThemeStore";

interface TopControlsProps {
	themeStore: ThemeStore;
	dbStore: DbStore;
}

export default observer(function TopControls({
	themeStore,
	dbStore,
}: TopControlsProps) {
	return (
		<div className={styles.container}>
			<EditModeButton store={dbStore} />
			<ThemeToggle store={themeStore} />
		</div>
	);
});
