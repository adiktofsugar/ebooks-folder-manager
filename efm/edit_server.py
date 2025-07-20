import logging
from pathlib import Path
import tempfile
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS
import yaml

from efm.tasks import TaskSetCover, TasksFile


logger = logging.getLogger(__name__)


def start_edit_server(tasks_filepath: Path, site_dirpath: Path, port: int = 8080):
    """Start Flask server for edit mode with add_task endpoint."""

    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    tasks_file = TasksFile(tasks_filepath)
    site_dirpath.mkdir(parents=True, exist_ok=True)
    edit_api_filepath = site_dirpath / "edit-db.yaml"
    edit_api_url = f"http://localhost:{port}"
    edit_db_data = dict(url=edit_api_url)
    edit_api_filepath.write_text(yaml.dump(edit_db_data))

    @app.route("/info", methods=["GET"])
    def get_info():
        """Get server info."""
        return jsonify(
            {
                "site_directory": str(site_dirpath),
            }
        )

    @app.route("/upload-cover-image", methods=["POST"])
    def upload_cover_image():
        """Upload cover image for a book."""
        try:
            # Check if image file was uploaded
            if "image" not in request.files:
                return jsonify({"error": "No image file provided"}), 400

            image_file = request.files["image"]
            if image_file.filename == "":
                return jsonify({"error": "No image selected"}), 400

            # Get book_filepath from form data
            book_filepath = request.form.get("book_filepath")
            if not book_filepath:
                return jsonify({"error": "No book_filepath provided"}), 400

            book_file = Path(book_filepath)
            if not book_file.exists():
                return jsonify({"error": f"Book file not found: {book_filepath}"}), 404

            # Save uploaded image to temporary file
            temp_dir = Path(tempfile.gettempdir())
            image_filename = f"cover_{uuid.uuid4().hex}.tmp"
            image_path = temp_dir / image_filename
            image_file.save(str(image_path))

            # Create task to set cover
            task = TaskSetCover(
                key="set_cover", book_filepath=book_file, cover_tmp_filepath=image_path
            )

            # Add task to tasks.jsonl
            tasks_file.add_task(task)

            # Return success response
            return jsonify(
                {
                    "status": "success",
                    "message": f"Cover update task created for {book_file.name}",
                    "task": task.to_dict(),
                }
            )

        except Exception as e:
            logger.error(f"Error handling cover upload: {e}")
            return jsonify({"error": f"Server error: {str(e)}"}), 500

    # Print server info
    print(f"\nStarting EFM API server on port {port}")
    print(f"Tasks will be saved to: {tasks_filepath}")
    print("\nAPI endpoints:")
    print(
        f"  GET  http://localhost:{port}/info                          - Get server info"
    )
    print(
        f"  POST http://localhost:{port}/upload-cover-image          - Upload cover image for book (with book_filepath)"
    )
    print("\nPress Ctrl+C to stop the server\n")

    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        # Clean up the API URL file
        if edit_api_filepath.exists():
            edit_api_filepath.unlink()
    return 0
