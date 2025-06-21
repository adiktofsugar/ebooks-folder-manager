# Email Worker

A Cloudflare Worker that receives emails via Cloudflare Email Routing and automatically archives them to Google Drive.

## Features

- Receives emails through Cloudflare Email Routing
- Streams email content directly to Google Drive (no memory buffering)
- Sends automatic replies on success or failure
- Detailed error reporting with trace IDs and debugging information
- Preserves original email format (.eml files)

## Prerequisites

### Google Cloud Setup

1. **Create a Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Note your project ID

2. **Enable Google Drive API**
   - In the Google Cloud Console, go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click on it and press "Enable"

3. **Create a Service Account**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the service account details:
     - Name: `email-worker-service-account` (or your preference)
     - Description: "Service account for Email Worker to upload to Google Drive"
   - Click "Create and Continue"
   - Skip the optional steps and click "Done"

4. **Generate Service Account Key**
   - Click on the service account you just created
   - Go to the "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose "JSON" format
   - Download the key file (keep this secure!)

5. **Create a Google Drive Folder**
   - Go to [Google Drive](https://drive.google.com)
   - Create a new folder for email archives
   - Right-click the folder and select "Share"
   - Share it with the service account email (found in your service account JSON file as `client_email`)
   - Grant "Editor" permissions
   - Copy the folder ID from the URL (e.g., `https://drive.google.com/drive/folders/FOLDER_ID_HERE`)

### Cloudflare Setup

1. **Domain Requirements**
   - You need a domain managed by Cloudflare
   - Email Routing must be available for your domain (free tier is sufficient)

2. **Enable Email Routing**
   - In Cloudflare Dashboard, go to your domain
   - Navigate to "Email" > "Email Routing"
   - Follow the setup wizard to enable Email Routing
   - Cloudflare will add the necessary MX records

3. **Deploy the Worker**
   ```bash
   cd email-worker
   npm install
   
   # Set secrets
   wrangler secret put GOOGLE_SERVICE_ACCOUNT_KEY
   # Paste the entire contents of your service account JSON file
   
   wrangler secret put GOOGLE_DRIVE_FOLDER_ID
   # Paste your Google Drive folder ID
   
   # Deploy
   wrangler deploy
   ```

4. **Configure Email Routing Rules**
   - In Cloudflare Dashboard, go to "Email" > "Email Routing" > "Routing Rules"
   - Click "Create rule"
   - Set up your rule:
     - **Match**: Choose your criteria (e.g., specific address like `archive@yourdomain.com`)
     - **Action**: Select "Send to Worker"
     - **Worker**: Select your deployed `email-worker`
   - Save the rule

## Configuration

### Environment Variables (Secrets)

- `GOOGLE_SERVICE_ACCOUNT_KEY`: The complete JSON key file for your Google service account
- `GOOGLE_DRIVE_FOLDER_ID`: The ID of the Google Drive folder where emails will be stored

### Wrangler Configuration

The `wrangler.toml` file contains:
- Worker name and entry point
- Compatibility date for Cloudflare Workers runtime
- Production environment configuration

## Usage

Once deployed and configured:

1. Send an email to your configured address (e.g., `archive@yourdomain.com`)
2. The worker will:
   - Receive the email
   - Stream it to Google Drive as an .eml file
   - Send you a confirmation email with the filename
3. If an error occurs, you'll receive an email with:
   - Error details and stack trace
   - Trace ID for debugging
   - Instructions to view logs in Cloudflare Dashboard

## File Naming

Emails are saved with the following format:
```
email_YYYY-MM-DDTHH-mm-ss-sssZ_subject.eml
```

Where:
- Timestamp is in ISO 8601 format
- Subject is sanitized (max 50 characters, alphanumeric only)
- Extension is `.eml` (standard email format)

## Debugging

### View Logs

1. **Via Cloudflare Dashboard**:
   - Go to Workers & Pages > your worker
   - Click on "Logs" tab
   - Search for the trace ID from error emails

2. **Via Wrangler CLI**:
   ```bash
   wrangler tail email-worker
   # Or search for specific trace ID
   wrangler tail email-worker --search "trace-id-here"
   ```

### Common Issues

1. **Authentication Errors**
   - Verify service account key is correctly set
   - Ensure Google Drive API is enabled
   - Check folder is shared with service account

2. **Permission Errors**
   - Verify service account has "Editor" access to the folder
   - Check folder ID is correct

3. **Email Routing Not Working**
   - Verify MX records are set correctly
   - Check email routing rules in Cloudflare
   - Ensure worker is deployed to production

## Security Considerations

- Service account keys are stored as encrypted Cloudflare secrets
- Emails are streamed directly to Google Drive (not stored in Worker)
- Original sender receives confirmation/error notifications only
- No email content is logged (only metadata like sender/subject)

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Deploy to production
npm run deploy

# View real-time logs
npm run tail
```

## Limitations

- Maximum email size depends on Cloudflare Workers limits (100MB request body)
- Processing time limited to Worker execution time (30 seconds)
- Google Drive API quotas apply (usually generous for this use case)