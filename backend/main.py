from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
import os
import asyncio

# Suppress TFLite and TensorFlow warnings in the console to clean up logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

app = FastAPI(title="CamEX")

# Construct the path to the frontend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
INDEX_PATH = os.path.join(FRONTEND_DIR, "index.html")
STYLE_PATH = os.path.join(FRONTEND_DIR, "style.css")

# Import state and queue
from backend.activity import activity_queue
from backend.experiment import ExperimentStateMachine, SAMPLE_EXPERIMENT, experiment_state
from backend.logger import experiment_logger
from backend.camera import reset_recording

active_websockets = []

@app.on_event("startup")
async def startup_event():
    # Start a background task to process the activity queue and broadcast state
    asyncio.create_task(process_activity_queue())

async def process_activity_queue():
    while True:
        if len(activity_queue) > 0:
            # We have a new activity
            event = activity_queue.popleft()
            
            # Determine step ID for logging
            if not experiment_state.completed:
                current_step_id = experiment_state.steps[experiment_state.current_step_index]["id"]
            else:
                current_step_id = "experiment_complete"
                
            result = experiment_state.advance(event["label"])
            
            # Record structured log entry
            if result["status"] == "ok":
                experiment_logger.log_event(current_step_id, "completed", event.get("confidence", 0.85), result["message"])
            elif result["status"] == "error" and "type" in result:
                experiment_logger.log_event(current_step_id, result["type"], event.get("confidence", 0.85), result["message"])
            
            # Broadcast the new state
            state = experiment_state.get_state()
            for ws in active_websockets:
                try:
                    await ws.send_json(state)
                except Exception:
                    pass
        await asyncio.sleep(0.1)

@app.get("/")
async def serve_frontend():
    """Serves the main frontend HTML page."""
    return FileResponse(INDEX_PATH)

@app.get("/style.css")
async def serve_style():
    """Serves the CSS file."""
    return FileResponse(STYLE_PATH)

@app.get("/app.js")
async def serve_app_js():
    """Serves the JavaScript file."""
    APP_PATH = os.path.join(FRONTEND_DIR, "app.js")
    return FileResponse(APP_PATH)

@app.get("/log")
async def get_log():
    """Returns the structured JSON logs."""
    return {"logs": experiment_logger.get_logs()}

@app.get("/state")
async def get_state():
    """REST endpoint to get current experiment state."""
    return experiment_state.get_state()

@app.post("/reset")
async def reset_experiment():
    """Resets the state machine and the video recording."""
    experiment_state.reset()
    activity_queue.clear()
    reset_recording()
    experiment_logger.log_event("system", "completed", 1.0, "Experiment reset.")
    
    # Broadcast new state
    state = experiment_state.get_state()
    for ws in active_websockets:
        try:
            await ws.send_json(state)
        except Exception:
            pass
            
    return {"status": "ok"}

@app.websocket("/ws/state")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint to push live state updates."""
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        # Send initial state immediately
        await websocket.send_json(experiment_state.get_state())
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)

# ----------------- REFERENCE OBJECTS SUBSYSTEM ----------------- #
from fastapi import UploadFile, File, Form
from backend.reference_objects import add_reference_image, get_reference_list, delete_reference

@app.post("/reference/upload")
async def upload_reference(label: str = Form(...), file: UploadFile = File(...)):
    """Uploads a reference image for custom object matching."""
    contents = await file.read()
    add_reference_image(label, contents)
    return {"status": "ok", "label": label, "message": f"Saved reference image for {label}"}

@app.get("/reference/list")
async def list_references():
    """Lists all custom object labels and their image counts."""
    return get_reference_list()

@app.delete("/reference/{label}")
async def remove_reference(label: str):
    """Removes a custom object label and all its embeddings."""
    delete_reference(label)
    return {"status": "ok", "label": label, "message": f"Deleted reference object {label}"}

@app.get("/video_feed")
async def video_feed():
    """MJPEG streaming endpoint."""
    from backend.camera import generate_frames
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
