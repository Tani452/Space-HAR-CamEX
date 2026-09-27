import os
import pickle
import torch
import torch.nn.functional as F
import open_clip
from PIL import Image
import io
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(BASE_DIR, "reference_objects")
EMBEDDINGS_FILE = os.path.join(REF_DIR, "embeddings.pkl")

if not os.path.exists(REF_DIR):
    os.makedirs(REF_DIR)

print("Initializing CLIP model for custom objects (ViT-B-32)...")
device = "cuda" if torch.cuda.is_available() else "cpu"
# This will download the weights locally the first time it's run
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai', device=device)
model.eval()

def load_embeddings():
    if os.path.exists(EMBEDDINGS_FILE):
        with open(EMBEDDINGS_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_embeddings(store):
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(store, f)

def compute_embedding(image_pil):
    """Computes and normalizes the CLIP image embedding."""
    image = preprocess(image_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image)
        # Normalize for cosine similarity
        image_features = F.normalize(image_features, p=2, dim=-1)
    return image_features.cpu()

def add_reference_image(label: str, image_bytes: bytes):
    """Saves a reference image and updates the embedding store."""
    label_dir = os.path.join(REF_DIR, label)
    if not os.path.exists(label_dir):
        os.makedirs(label_dir)
        
    num_existing = len(os.listdir(label_dir))
    image_path = os.path.join(label_dir, f"{num_existing}.jpg")
    
    image_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_pil.save(image_path)
    
    emb = compute_embedding(image_pil)
    
    store = load_embeddings()
    if label not in store:
        store[label] = []
    store[label].append(emb)
    save_embeddings(store)

def get_reference_list():
    """Returns a dict of labels and the count of their reference images."""
    store = load_embeddings()
    return {label: len(embs) for label, embs in store.items()}

def delete_reference(label: str):
    """Deletes a label and all its associated reference images/embeddings."""
    store = load_embeddings()
    if label in store:
        del store[label]
        save_embeddings(store)
        
    label_dir = os.path.join(REF_DIR, label)
    if os.path.exists(label_dir):
        shutil.rmtree(label_dir)

def match_embedding(crop_embedding, threshold=0.75):
    """
    Compares a target embedding against all reference embeddings using cosine similarity.
    Returns a tuple (best_matching_label, similarity_score).
    If no match exceeds the threshold, returns (None, highest_similarity_score).
    """
    store = load_embeddings()
    if not store:
        return None, 0.0
        
    best_label = None
    best_sim = -1.0
    
    # crop_embedding should already be normalized
    for label, embs in store.items():
        for ref_emb in embs:
            # Cosine similarity (since both are normalized, it's just the dot product)
            sim = torch.sum(crop_embedding * ref_emb).item()
            if sim > best_sim:
                best_sim = sim
                best_label = label
                
    if best_sim >= threshold:
        return best_label, best_sim
        
    return None, best_sim
