import cv2
from PIL import Image
from ultralytics import YOLO
from backend.reference_objects import compute_embedding, match_embedding

class ObjectDetector:
    def __init__(self, model_path="yolov8n.pt"):
        self.model = YOLO(model_path)
    
    def process_frame(self, frame):
        """
        Runs YOLO detection, but treats the YOLO class as a fallback.
        For each box, it computes a CLIP embedding and matches against custom references.
        """
        # Run inference
        results = self.model(frame, verbose=False)
        annotated_frame = frame.copy()
        
        boxes_data = []
        if len(results[0].boxes) > 0:
            for box in results[0].boxes:
                # get bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                conf = float(box.conf[0].item())
                cls_idx = int(box.cls[0].item())
                yolo_label = self.model.names[cls_idx]
                
                # Exclude 'person' class from activity tracking so hands don't trigger on astronaut body,
                # but STILL draw it on the frame so it appears on the dashboard normally.
                if yolo_label == 'person':
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 100, 100), 2)
                    label_text = f"person {conf:.2f}"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(annotated_frame, (x1, y1 - th - 5), (x1 + tw, y1), (255, 100, 100), -1)
                    cv2.putText(annotated_frame, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    continue
                
                # --- CUSTOM MATCHING PIPELINE (For non-person objects) ---
                h, w, _ = frame.shape
                cx1, cy1 = max(0, x1), max(0, y1)
                cx2, cy2 = min(w, x2), min(h, y2)
                
                if cx2 > cx1 and cy2 > cy1:
                    # Crop and convert to PIL Image
                    crop = frame[cy1:cy2, cx1:cx2]
                    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    crop_pil = Image.fromarray(crop_rgb)
                    
                    # Compute embedding and check for custom match
                    # Increased threshold from 0.75 to 0.88 to filter out false positives like tables
                    emb = compute_embedding(crop_pil)
                    custom_label, sim_score = match_embedding(emb, threshold=0.88)
                else:
                    custom_label, sim_score = None, 0.0
                
                if custom_label is not None:
                    # It's a confirmed custom object
                    final_label = custom_label
                    final_score = sim_score
                    color = (0, 255, 0) # Green for verified custom object
                    
                    # Store standardized box dict
                    boxes_data.append({
                        "bbox": (x1, y1, x2, y2),
                        "class": final_label,
                        "confidence": final_score
                    })
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw custom label and confidence score
                    label_text = f"{final_label} {final_score:.2f}"
                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(annotated_frame, (x1, y1 - th - 5), (x1 + tw, y1), color, -1)
                    cv2.putText(annotated_frame, label_text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    # Unconfirmed object: COMPLETELY IGNORE. 
                    # No box drawn, no label, not added to boxes_data, no event triggered.
                    continue
                
        return annotated_frame, boxes_data

# Singleton instance to avoid reloading the model on every frame
detector = ObjectDetector()

def detect_objects(frame):
    return detector.process_frame(frame)
