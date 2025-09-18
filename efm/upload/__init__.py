from collections.abc import Mapping
from hashlib import sha256
import os
from pathlib import Path
from base64 import b64encode
import mimetypes
from cloudflare import Cloudflare
from cloudflare.types.workers.scripts.assets.upload_create_params import Manifest
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
)


def upload_to_cloudflare_worker(
    site_dir: Path,
    *,
    account_id: str,
    api_token: str,
    script_name: str,
):
    client = Cloudflare(api_token=api_token)
    # there's a limitation with this method, which is
    #   that we can't have over 20k entries. ...that
    #   seems a bit extreme, but I can definitely imagine
    #   having that many ebooks.
    # an alternative may be to make a worker that just streams
    #   from r2, but I suspect that's not _quite_ as free
    manifest: Mapping[str, Manifest] = {}
    file_contents: Mapping[str, bytes] = {}
    skipped_files = []
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB limit

    # Initialize mimetypes
    if not mimetypes.inited:
        mimetypes.init()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        transient=False,
    ) as progress:
        # Scan files and build manifest
        scan_task = progress.add_task("Scanning files...", total=None)
        for root, dirs, files in os.walk(site_dir):
            for file in files:
                src_file = Path(root) / file
                file_size = src_file.stat().st_size
                hash = str(src_file.relative_to(site_dir).as_posix())

                # Skip files that are too large
                if file_size > MAX_FILE_SIZE:
                    skipped_files.append((hash, file_size))
                    continue

                with open(src_file, "rb") as f:
                    content = f.read()
                    file_contents[hash] = content
                    # Generate hash like in the TS example - first 32 chars of hex
                    # They hash the base64 content + extension
                    extension = Path(hash).suffix
                    content_to_hash = b64encode(content).decode("ascii") + extension
                    hash_hex = sha256(
                        content_to_hash.encode(), usedforsecurity=False
                    ).hexdigest()[:32]
                    manifest[hash] = {
                        "size": len(content),
                        "hash": hash_hex,
                    }
        progress.update(scan_task, completed=1, total=1)

        if skipped_files:
            raise Exception(
                f"Skipped {len(skipped_files)} files over 25MB:\n"
                + "\n".join(
                    f"- {path} ({size / 1024 / 1024:.1f}MB)"
                    for path, size in skipped_files
                )
            )

        # Create upload session
        create_task = progress.add_task(
            f"Creating upload session for {len(manifest)} files...", total=1
        )
        upload = client.workers.scripts.assets.upload.create(
            script_name=script_name, account_id=account_id, manifest=manifest
        )
        progress.update(create_task, completed=1)

        if not upload or not upload.jwt or not upload.buckets:
            raise Exception("Failed to start upload session")

        completion_jwt: str | None = None
        upload_task = progress.add_task("Uploading files", total=len(file_contents))
        for bucket in upload.buckets:
            payload: dict[str, str] = {}
            for hash in bucket:
                if hash in file_contents:
                    content_type = (
                        mimetypes.guess_type(hash)[0] or "application/octet-stream"
                    )
                    payload[hash] = b64encode(file_contents[hash]).decode("ascii")
            upload_response = client.workers.assets.upload.create(
                account_id=account_id,
                base64=True,
                body=payload,
                extra_headers=dict(Authorization=f"Bearer {upload.jwt}"),
            )
            if upload_response:
                completion_jwt = upload_response.jwt
            progress.advance(upload_task, len(payload))

        if not completion_jwt:
            raise Exception("Upload completed but no completion JWT received")

        # Deploy the script with uploaded assets
        deploy_task = progress.add_task(f"Deploying script {script_name}...", total=1)

        script_content = """
            export default {
                async fetch(request, env, ctx) {
                    return new Response("Hello", { status: 200 });
                }
            };
            """
        # Deploy script that serves static assets
        deploy_response = client.workers.scripts.update(
            script_name=script_name,
            account_id=account_id,
            files={
                "index.js": (
                    "index.js",
                    bytes(script_content, "utf-8"),
                    "application/javascript+module",
                )
            },
            metadata={
                "main_module": "index.js",
                "assets": {"jwt": completion_jwt},
                "compatibility_date": "2025-09-18",
            },
        )

        progress.update(deploy_task, completed=1)

    print(
        f"✅ Successfully deployed to https://{script_name}.{account_id.split('-')[0]}.workers.dev"
    )
