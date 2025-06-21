import type { JsonObject } from "type-fest";
interface ServiceAccountKey {
	type: string;
	project_id: string;
	private_key_id: string;
	private_key: string;
	client_email: string;
	client_id: string;
	auth_uri: string;
	token_uri: string;
	auth_provider_x509_cert_url: string;
	client_x509_cert_url: string;
}

export class GoogleDriveService {
	private serviceAccount: ServiceAccountKey;
	private folderId: string;
	private accessToken: string | null = null;
	private tokenExpiry = 0;

	constructor(serviceAccount: ServiceAccountKey, folderId: string) {
		this.serviceAccount = serviceAccount;
		this.folderId = folderId;
	}

	private async getAccessToken(): Promise<string> {
		// Check if we have a valid cached token
		if (this.accessToken && Date.now() < this.tokenExpiry) {
			return this.accessToken;
		}

		// Create JWT
		const header = {
			alg: "RS256",
			typ: "JWT",
		};

		const now = Math.floor(Date.now() / 1000);
		const payload = {
			iss: this.serviceAccount.client_email,
			scope: "https://www.googleapis.com/auth/drive.file",
			aud: this.serviceAccount.token_uri,
			exp: now + 3600, // 1 hour
			iat: now,
		};

		// Sign JWT
		const jwt = await this.createJWT(header, payload);

		// Exchange JWT for access token
		const response = await fetch(this.serviceAccount.token_uri, {
			method: "POST",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded",
			},
			body: new URLSearchParams({
				grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
				assertion: jwt,
			}),
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`Failed to get access token: ${error}`);
		}

		const data = (await response.json()) as {
			access_token: string;
			expires_in: number;
		};
		this.accessToken = data.access_token;
		this.tokenExpiry = Date.now() + (data.expires_in - 60) * 1000; // Subtract 60 seconds for safety

		return this.accessToken;
	}

	private async createJWT(
		header: JsonObject,
		payload: JsonObject,
	): Promise<string> {
		const encoder = new TextEncoder();

		// Base64url encode header and payload
		const encodedHeader = this.base64urlEncode(JSON.stringify(header));
		const encodedPayload = this.base64urlEncode(JSON.stringify(payload));

		const message = `${encodedHeader}.${encodedPayload}`;

		// Import the private key
		const keyData = this.pemToArrayBuffer(this.serviceAccount.private_key);
		const cryptoKey = await crypto.subtle.importKey(
			"pkcs8",
			keyData,
			{
				name: "RSASSA-PKCS1-v1_5",
				hash: "SHA-256",
			},
			false,
			["sign"],
		);

		// Sign the message
		const signature = await crypto.subtle.sign(
			"RSASSA-PKCS1-v1_5",
			cryptoKey,
			encoder.encode(message),
		);

		// Base64url encode the signature
		const encodedSignature = this.base64urlEncode(signature);

		return `${message}.${encodedSignature}`;
	}

	private pemToArrayBuffer(pem: string): ArrayBuffer {
		const b64 = pem
			.replace(/-----BEGIN PRIVATE KEY-----/, "")
			.replace(/-----END PRIVATE KEY-----/, "")
			.replace(/\s/g, "");

		const binaryString = atob(b64);
		const bytes = new Uint8Array(binaryString.length);

		for (let i = 0; i < binaryString.length; i++) {
			bytes[i] = binaryString.charCodeAt(i);
		}

		return bytes.buffer;
	}

	private base64urlEncode(input: string | ArrayBuffer): string {
		let b64: string;

		if (typeof input === "string") {
			b64 = btoa(input);
		} else {
			const bytes = new Uint8Array(input);
			let binary = "";
			for (let i = 0; i < bytes.length; i++) {
				binary += String.fromCharCode(bytes[i]);
			}
			b64 = btoa(binary);
		}

		return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
	}

	async uploadStream(
		filename: string,
		stream: ReadableStream<Uint8Array>,
		mimeType: string,
		estimatedSize?: number,
	): Promise<void> {
		const token = await this.getAccessToken();

		// Use resumable upload for streaming
		// Step 1: Initiate resumable upload
		const metadata = {
			name: filename,
			parents: [this.folderId],
			mimeType: mimeType,
		};

		const initResponse = await fetch(
			"https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
			{
				method: "POST",
				headers: {
					Authorization: `Bearer ${token}`,
					"Content-Type": "application/json",
					"X-Upload-Content-Type": mimeType,
					...(estimatedSize && {
						"X-Upload-Content-Length": estimatedSize.toString(),
					}),
				},
				body: JSON.stringify(metadata),
			},
		);

		if (!initResponse.ok) {
			const error = await initResponse.text();
			throw new Error(`Failed to initiate upload: ${error}`);
		}

		const uploadUrl = initResponse.headers.get("Location");
		if (!uploadUrl) {
			throw new Error("No upload URL returned");
		}

		// Step 2: Stream upload the content
		const uploadResponse = await fetch(uploadUrl, {
			method: "PUT",
			headers: {
				"Content-Type": mimeType,
			},
			body: stream,
		});

		if (!uploadResponse.ok) {
			const error = await uploadResponse.text();
			throw new Error(`Failed to upload file: ${error}`);
		}

		console.log("File uploaded successfully");
	}

	// Fallback method for smaller files
	async uploadFile(
		filename: string,
		content: Uint8Array,
		mimeType: string,
	): Promise<void> {
		const token = await this.getAccessToken();

		// Create multipart body
		const metadata = {
			name: filename,
			parents: [this.folderId],
		};

		const boundary = "-------314159265358979323846";
		const delimiter = `\r\n--${boundary}\r\n`;
		const closeDelimiter = `\r\n--${boundary}--`;

		const metadataString = JSON.stringify(metadata);

		// Convert content to base64
		let binary = "";
		for (let i = 0; i < content.length; i++) {
			binary += String.fromCharCode(content[i]);
		}
		const base64Data = btoa(binary);

		const multipartBody = `${delimiter}Content-Type: application/json; charset=UTF-8\r\n\r\n${metadataString}${delimiter}Content-Type: ${mimeType}\r\nContent-Transfer-Encoding: base64\r\n\r\n${base64Data}${closeDelimiter}`;

		const response = await fetch(
			"https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
			{
				method: "POST",
				headers: {
					Authorization: `Bearer ${token}`,
					"Content-Type": `multipart/related; boundary="${boundary}"`,
				},
				body: multipartBody,
			},
		);

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`Failed to upload file: ${error}`);
		}
	}
}
