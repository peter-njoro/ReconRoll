from face_utils import load_known_faces
import time

print("🔄 Starting test...")
start_time = time.time()

known_face_encodings, known_face_names, id_card_cache = load_known_faces(
    './uploads/faces/',
    './uploads/faces/cards/',
    scale=0.5
)

print(f"✅ Completed in {time.time()-start_time:.2f} seconds")
print(f"Loaded {len(known_face_encodings)} faces")