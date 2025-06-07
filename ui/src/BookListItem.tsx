import { observer } from "mobx-react-lite";

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
		<div>
			<p>
				Title:{" "}
				{/* biome-ignore lint/security/noDangerouslySetInnerHtml: fuzzy changes html */}
				<span dangerouslySetInnerHTML={{ __html: title }} />
			</p>
			<p>
				Author:{" "}
				{/* biome-ignore lint/security/noDangerouslySetInnerHtml: fuzzy changes html */}
				<span dangerouslySetInnerHTML={{ __html: author }} />
			</p>
			<a href={new URL(filename, location.href).href}>Download</a>
		</div>
	);
});
