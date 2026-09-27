import time
import math
from collections import deque

# Simple in-process queue for activity events
activity_queue = deque(maxlen=100)

class ActivityRecognizer:
    def __init__(self, contact_threshold=250.0, placed_frames_threshold=10):
        self.contact_threshold = contact_threshold
        self.placed_frames_threshold = placed_frames_threshold
        
        # State tracking per object class: 
        # { "object_class": {"zone": "unknown", "placed_frames": 0, "was_in_hand": False} }
        self.object_states = {}

    def get_hand_centers(self, hands, frame_w, frame_h):
        centers = []
        for hand in hands:
            # Use wrist (landmark 0) as the hand center
            cx = hand[0]['x'] * frame_w
            cy = hand[0]['y'] * frame_h
            centers.append((cx, cy))
        return centers

    def get_box_center(self, box):
        x1, y1, x2, y2 = box
        return (x1 + x2) / 2, (y1 + y2) / 2
        
    def get_zone(self, cx, w):
        if cx < w / 3.0:
            return "storage"
        elif cx > 2.0 * w / 3.0:
            return "workstation"
        else:
            return "transit"

    def process(self, boxes, hands, frame_shape):
        h, w, _ = frame_shape
        hand_centers = self.get_hand_centers(hands, w, h)
        
        for obj in boxes:
            cls = obj['class']
            box = obj['bbox']
            
            obj_center = self.get_box_center(box)
            cx, cy = obj_center
            
            # Check if hand is near
            in_hand = False
            for hc in hand_centers:
                dist = math.hypot(hc[0] - cx, hc[1] - cy)
                if dist < self.contact_threshold:
                    in_hand = True
                    break
                    
            current_zone = self.get_zone(cx, w)
            
            if cls not in self.object_states:
                self.object_states[cls] = {"zone": "unknown", "placed_frames": 0, "was_in_hand": False}
                
            state_info = self.object_states[cls]
            last_zone = state_info["zone"]
            
            # Initialize zone if unknown
            if last_zone == "unknown":
                state_info["zone"] = current_zone
                state_info["was_in_hand"] = in_hand
                continue
                
            # 1. Retrieved
            if last_zone == "storage" and current_zone != "storage" and in_hand:
                self.emit_event("retrieved", cls)
                
            # 2. Transferred
            if last_zone != "workstation" and current_zone == "workstation":
                self.emit_event("transferred", cls)
                
            # 3. Placed
            if current_zone == "workstation":
                if not in_hand:
                    state_info["placed_frames"] += 1
                    if state_info["placed_frames"] == self.placed_frames_threshold:
                        self.emit_event("placed", cls)
                else:
                    state_info["placed_frames"] = 0
            else:
                state_info["placed_frames"] = 0
                
            # 4. Returned
            if last_zone != "storage" and current_zone == "storage":
                self.emit_event("returned", cls)
                
            # Update state
            state_info["zone"] = current_zone
            state_info["was_in_hand"] = in_hand

    def emit_event(self, action, obj_class):
        event = {
            "label": f"{action} {obj_class}",
            "timestamp": time.time(),
            "confidence": 0.90
        }
        activity_queue.append(event)
        print(f"\n>>> ACTIVITY DETECTED: {event['label']} at {time.strftime('%H:%M:%S', time.localtime(event['timestamp']))}\n")

# Singleton instance
recognizer = ActivityRecognizer()

def detect_activities(boxes, hands, frame_shape):
    recognizer.process(boxes, hands, frame_shape)
