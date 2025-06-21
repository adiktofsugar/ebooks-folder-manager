import { EmailMessage } from "cloudflare:email";
import { createMimeMessage } from "mimetext";
import { GoogleDriveService } from "./google-drive";

export interface Env {
	GOOGLE_SERVICE_ACCOUNT_KEY: string;
	GOOGLE_DRIVE_FOLDER_ID: string;
}

export default {
	async email(
		message: EmailMessage,
		env: Env,
		ctx: ExecutionContext,
	): Promise<void> {
		const startTime = Date.now();
		const traceId = crypto.randomUUID();

		try {
			console.log(
				`[${traceId}] Received email from: ${message.from}, to: ${message.to}`,
			);
			console.log(`[${traceId}] Subject: ${message.headers.get("subject")}`);

			// Initialize Google Drive service
			const driveService = new GoogleDriveService(
				JSON.parse(env.GOOGLE_SERVICE_ACCOUNT_KEY),
				env.GOOGLE_DRIVE_FOLDER_ID,
			);

			// Generate filename with timestamp
			const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
			const subject = message.headers.get("subject") || "no-subject";
			const sanitizedSubject = subject
				.replace(/[^a-zA-Z0-9-_]/g, "_")
				.slice(0, 50);
			const filename = `email_${timestamp}_${sanitizedSubject}.eml`;

			// Get size hint if available
			const contentLength = message.headers.get("content-length");
			const estimatedSize = contentLength
				? Number.parseInt(contentLength, 10)
				: undefined;

			// Stream email content directly to Google Drive
			console.log(`[${traceId}] Starting streaming upload to Google Drive`);
			await driveService.uploadStream(
				filename,
				message.raw,
				"message/rfc822",
				estimatedSize,
			);

			console.log(
				`[${traceId}] Email uploaded to Google Drive as: ${filename}`,
			);

			// Send success reply
			if (message.headers.get("auto-submitted") !== "auto-replied") {
				await sendSuccessReply(message, filename);
			}
		} catch (error) {
			console.error(`[${traceId}] Error processing email:`, error);

			// Send error reply with details
			try {
				await sendErrorReply(message, error, traceId, startTime);
			} catch (replyError) {
				console.error(`[${traceId}] Failed to send error reply:`, replyError);
			}

			// Re-throw to ensure the error is logged in Cloudflare dashboard
			throw error;
		}
	},
};

async function sendSuccessReply(
	message: EmailMessage,
	filename: string,
): Promise<void> {
	const msg = createMimeMessage();
	msg.setSender({ name: "Email Archive Bot", addr: message.to });
	msg.setRecipient(message.from);
	msg.setSubject(`Re: ${message.headers.get("subject") || "Your email"}`);
	msg.addMessage({
		contentType: "text/plain",
		data: `Your email has been successfully archived to Google Drive as:\n${filename}`,
	});
	msg.setHeader("Auto-Submitted", "auto-replied");
	msg.setHeader("In-Reply-To", message.headers.get("message-id") || "");

	const reply = new EmailMessage(message.to, message.from, msg.asRaw());
	await message.reply(reply);
}

async function sendErrorReply(
	message: EmailMessage,
	error: unknown,
	traceId: string,
	startTime: number,
): Promise<void> {
	const duration = Date.now() - startTime;
	const errorMessage = error instanceof Error ? error.message : String(error);
	const stackTrace =
		error instanceof Error ? error.stack : "No stack trace available";

	// Get worker name from the email address or use default
	const workerName = message.to.split("@")[0] || "email-worker";

	const msg = createMimeMessage();
	msg.setSender({ name: "Email Archive Bot (Error)", addr: message.to });
	msg.setRecipient(message.from);
	msg.setSubject(
		`ERROR: Failed to archive - ${message.headers.get("subject") || "Your email"}`,
	);

	const errorBody = `Failed to archive your email to Google Drive.

Error Details:
--------------
Trace ID: ${traceId}
Duration: ${duration}ms
Error: ${errorMessage}

Stack Trace:
------------
${stackTrace}

Debugging Information:
---------------------
To view logs for this execution:
1. Go to Cloudflare Dashboard
2. Navigate to Workers & Pages > ${workerName}
3. Go to Logs tab
4. Search for trace ID: ${traceId}

Or use wrangler CLI:
wrangler tail ${workerName} --search "${traceId}"

The original email has been preserved and this error has been logged.`;

	msg.addMessage({
		contentType: "text/plain",
		data: errorBody,
	});

	msg.setHeader("Auto-Submitted", "auto-replied");
	msg.setHeader("In-Reply-To", message.headers.get("message-id") || "");
	msg.setHeader("X-Trace-ID", traceId);

	const reply = new EmailMessage(message.to, message.from, msg.asRaw());
	await message.reply(reply);
}
