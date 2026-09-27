import cv2
import os
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Define connections manually since mediapipe legacy drawing utils are completely missing in Python 3.14 builds
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), # thumb
    (0, 5), (5, 6), (6, 7), (7, 8), # index
    (5, 9), (9, 10), (10, 11), (11, 12), # middle
    (9, 13), (13, 14), (14, 15), (15, 16), # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # pinky
]

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32)
]

class PoseDetector:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pose_model_path = os.path.join(base_dir, 'pose_landmarker.task')
        hand_model_path = os.path.join(base_dir, 'hand_landmarker.task')
        
        # We need the task files to be downloaded first
        if not os.path.exists(pose_model_path) or not os.path.exists(hand_model_path):
            print("Warning: MediaPipe task files not found. Detection will be bypassed until they are downloaded.")
            self.pose_landmarker = None
            self.hand_landmarker = None
            return

        # Initialize Pose Landmarker
        pose_base_options = python.BaseOptions(model_asset_path=pose_model_path)
        pose_options = vision.PoseLandmarkerOptions(
            base_options=pose_base_options,
            output_segmentation_masks=False)
        self.pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)
        
        # Initialize Hand Landmarker
        hand_base_options = python.BaseOptions(model_asset_path=hand_model_path)
        hand_options = vision.HandLandmarkerOptions(
            base_options=hand_base_options,
            num_hands=2)
        self.hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)

    def draw_landmarks(self, frame, landmarks_list, connections, color=(0, 255, 0)):
        h, w, _ = frame.shape
        for landmarks in landmarks_list:
            # Draw points
            points = []
            for lm in landmarks:
                x, y = int(lm.x * w), int(lm.y * h)
                points.append((x, y))
                cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)
                
            # Draw connections
            for connection in connections:
                start_idx, end_idx = connection
                if start_idx < len(points) and end_idx < len(points):
                    cv2.line(frame, points[start_idx], points[end_idx], color, 2)

    def process_frame(self, frame):
        if not self.pose_landmarker or not self.hand_landmarker:
            return frame

        # Convert the frame to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        # Detect
        pose_result = self.pose_landmarker.detect(mp_image)
        hand_result = self.hand_landmarker.detect(mp_image)
        
        annotated_frame = frame.copy()
        
        # Draw Pose
        if pose_result.pose_landmarks:
            self.draw_landmarks(annotated_frame, pose_result.pose_landmarks, POSE_CONNECTIONS, color=(0, 255, 0))
            
        hand_landmarks_out = []
        # Draw Hands
        if hand_result.hand_landmarks:
            self.draw_landmarks(annotated_frame, hand_result.hand_landmarks, HAND_CONNECTIONS, color=(255, 0, 0))
            for hl in hand_result.hand_landmarks:
                pts = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in hl]
                hand_landmarks_out.append(pts)
            
        return annotated_frame, hand_landmarks_out

# Singleton instance
detector = PoseDetector()

def detect_pose(frame):
    return detector.process_frame(frame)
