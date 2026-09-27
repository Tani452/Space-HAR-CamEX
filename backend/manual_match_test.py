import argparse
import sys
from PIL import Image
import os

# Ensure the root directory is in sys.path so we can import 'backend'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.reference_objects import compute_embedding, match_embedding

def main():
    parser = argparse.ArgumentParser(description="Test CLIP embedding matching for an image.")
    parser.add_argument("image_path", type=str, help="Path to the test image")
    parser.add_argument("--threshold", type=float, default=0.75, help="Matching threshold (default: 0.75)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.image_path):
        print(f"Error: Image not found at {args.image_path}")
        return
        
    print(f"Loading test image from {args.image_path}...")
    try:
        image = Image.open(args.image_path).convert("RGB")
    except Exception as e:
        print(f"Error loading image: {e}")
        return
        
    print("Computing CLIP embedding...")
    emb = compute_embedding(image)
    
    print("Comparing against reference library...")
    best_label, best_sim = match_embedding(emb, threshold=args.threshold)
    
    if best_label is not None:
        print(f"\n✅ MATCH FOUND")
        print(f"Label: '{best_label}'")
        print(f"Similarity Score: {best_sim:.4f}")
    else:
        print(f"\n❌ NO MATCH")
        print(f"Highest similarity found: {best_sim:.4f}")
        print(f"(Threshold was set to {args.threshold})")

if __name__ == "__main__":
    main()
