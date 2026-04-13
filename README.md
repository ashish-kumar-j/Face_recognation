# Face Recognition App v1

Local FastAPI app for webcam-based face identification against a known-faces database.

## Features
- Local email/password auth with admin/operator roles
- Known-person enrollment via webcam frames or uploaded photos
- Continuous live recognition over WebSocket
- Strict identity mode with unknown fallback
- Basic liveness heuristic (motion + eye landmark signal)
- Recognition event logging with optional unknown snapshots
- Signed webhook outbox with retry/backoff
- SQLite storage

## Quick Start (Python 3.11)
1. Create a Python 3.11 virtual environment.
2. Install dependencies:
   - `pip install -e .[dev]`
   - Optional for real face model: `pip install -e .[insightface]`
3. Run the app:
   - `uvicorn app.main:app --reload`
4. Open `http://127.0.0.1:8000`.

## Notes
- If `insightface` is not installed, the app uses a deterministic fallback embedding engine for development/testing.
- Webcam access happens in the browser (`getUserMedia`) and frames are streamed to the backend.
- First registered user is bootstrap admin.
