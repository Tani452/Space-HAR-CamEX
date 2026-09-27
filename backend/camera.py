import cv2
import os
import time

# Import the detection function from our new module
from backend.detection import detect_objects
from backend.pose import detect_pose
from backend.activity import detect_activities
from backend.experiment import experiment_state

# Configuration flags to toggle detection overlays
USE_DETECTION = True
USE_POSE = True
USE_ACTIVITY = True

# Setup recordings directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
if not os.path.exists(RECORDINGS_DIR):
    os.makedirs(RECORDINGS_DIR)

video_writer = None

def reset_recording():
    global video_writer
    if video_writer is not None:
        video_writer.release()
        video_writer = None

def generate_frames():
    global video_writer
    print("Initializing camera...")
    # Try default backend first, on Windows sometimes CAP_DSHOW is needed
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not camera.isOpened():
        print("Warning: Could not open camera with DSHOW, trying default backend...")
        camera = cv2.VideoCapture(0)
        
    if not camera.isOpened():
        print("Error: Could not open camera. Is it connected and not used by another app?")
        return

    # Reduce resolution to 640x480 for much faster AI processing and less lag
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Camera opened successfully.")
    try:
        while True:
            success, frame = camera.read()
            if not success:
                print("Error: Failed to read frame from camera.")
                break
            
            try:
                boxes = []
                hands = []
                
                # Apply YOLO detection if enabled
                if USE_DETECTION:
                    frame, boxes = detect_objects(frame)
                    
                # Apply MediaPipe pose and hands detection if enabled
                if USE_POSE:
                    frame, hands = detect_pose(frame)
                    
                # Apply activity detection
                if USE_ACTIVITY:
                    detect_activities(boxes, hands, frame.shape)
                    
                # Draw Storage and Workstation Zones
                h, w, _ = frame.shape
                overlay = frame.copy()
                # Storage zone (Left 1/3) - Reddish
                cv2.rectangle(overlay, (0, 0), (int(w/3), h), (0, 0, 255), -1)
                # Workstation zone (Right 1/3) - Bluish
                cv2.rectangle(overlay, (int(2*w/3), 0), (w, h), (255, 0, 0), -1)
                
                # Blend with original
                cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
                
                # Add text labels
                cv2.putText(frame, "STORAGE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 255), 2)
                cv2.putText(frame, "WORKSTATION", (int(2*w/3) + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 200), 2)
                    
                # ---------------- RECORDING LOGIC ---------------- #
                # If experiment is active and we don't have a writer, create one
                if not experiment_state.completed and video_writer is None:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(RECORDINGS_DIR, f"experiment_{timestamp}.mp4")
                    # mp4v codec is standard for mp4 in OpenCV
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    h, w, _ = frame.shape
                    
                    # We set FPS to 10.0 to match the approximate speed of the YOLO+MediaPipe inference.
                    # If we set it to 30.0 or 20.0, but only generate 10 frames per second due to AI processing,
                    # the resulting video plays back in fast-forward.
                    video_writer = cv2.VideoWriter(filename, fourcc, 10.0, (w, h))
                    print(f"Started recording: {filename}")
                    
                # If experiment is complete and we have a writer, release it
                if experiment_state.completed and video_writer is not None:
                    video_writer.release()
                    video_writer = None
                    print("Experiment completed. Recording successfully saved to disk.")
                    
                # Write the annotated frame to disk if recording is active
                if video_writer is not None:
                    video_writer.write(frame)
                # ------------------------------------------------- #
                    
            except Exception as e:
                print(f"Error during AI processing: {e}")
                import traceback
                traceback.print_exc()
            
            # Encode the frame in JPEG format for the web stream
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
                
            frame_bytes = buffer.tobytes()
            
            # Yield the frame in the MJPEG multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        if video_writer is not None:
            video_writer.release()
            video_writer = None
        camera.release()
