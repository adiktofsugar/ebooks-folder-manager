import { observer } from "mobx-react-lite";
import { useEffect } from "react";
import type { DbMeta } from "./interfaces";

export default observer(function EditModeInfo({ meta }: { meta: DbMeta }) {
	return (
		<ul>
			<li>
				<b>Site Directory:</b> {meta.site_dirpath}
			</li>
		</ul>
	);
});
