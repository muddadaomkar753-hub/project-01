import cv2
import numpy as np
import base64
import os
import re
from typing import List, Dict, Tuple, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BASE_DIR, "models")

YUNET_PATH = os.path.join(MODELS_DIR, "face_detection_yunet.onnx")
SFACE_PATH = os.path.join(MODELS_DIR, "face_recognition_sface.onnx")

class FaceEngine:
    def __init__(self):
        self.detector = None
        self.recognizer = None
        self.haar_cascade = None
        self._init_models()

    def _init_models(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        if not os.path.exists(YUNET_PATH) or os.path.getsize(YUNET_PATH) < 1000:
            self._download_model(
                "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                YUNET_PATH
            )
        if not os.path.exists(SFACE_PATH) or os.path.getsize(SFACE_PATH) < 1000000:
            self._download_model(
                "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
                SFACE_PATH
            )

        if os.path.exists(YUNET_PATH) and os.path.exists(SFACE_PATH):
            try:
                # Default input size (320, 320) - will be updated dynamically per image
                self.detector = cv2.FaceDetectorYN.create(
                    model=YUNET_PATH,
                    config="",
                    input_size=(320, 320),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=5000
                )
                self.recognizer = cv2.FaceRecognizerSF.create(
                    model=SFACE_PATH,
                    config=""
                )
                print("[FaceEngine] Successfully initialized YuNet detector & SFace recognizer.")
            except Exception as e:
                print(f"[FaceEngine] Error initializing ONNX models: {e}")
        
        # Initialize Haar Cascade as fallback
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.haar_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"[FaceEngine] Error loading Haar Cascade: {e}")

    @staticmethod
    def _download_model(url: str, dest_path: str):
        try:
            import urllib.request
            print(f"[FaceEngine] Downloading model to {dest_path}...")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
                f.write(resp.read())
            print(f"[FaceEngine] Model downloaded successfully.")
        except Exception as e:
            print(f"[FaceEngine] Could not download model from {url}: {e}")

    @staticmethod
    def decode_base64_image(image_data: str) -> Optional[np.ndarray]:
        """Converts base64 data URL or raw base64 string to BGR OpenCV image."""
        try:
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[FaceEngine] Error decoding base64 image: {e}")
            return None

    @staticmethod
    def assess_quality(img: np.ndarray, bbox: Optional[List[int]] = None) -> Dict[str, Any]:
        """Calculates blur (Laplacian variance) and brightness metrics."""
        if bbox:
            x, y, w, h = bbox
            h_img, w_img = img.shape[:2]
            x, y = max(0, x), max(0, y)
            w, h = min(w, w_img - x), min(h, h_img - y)
            roi = img[y:y+h, x:x+w]
            if roi.size > 0:
                target = roi
            else:
                target = img
        else:
            target = img

        gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = float(np.mean(gray))

        is_blurry = blur_score < 40.0
        is_too_dark = brightness < 40.0
        is_too_bright = brightness > 220.0

        return {
            "blur_score": round(float(blur_score), 2),
            "brightness": round(brightness, 2),
            "is_acceptable": (not is_blurry) and (not is_too_dark) and (not is_too_bright),
            "quality_note": (
                "Image too blurry" if is_blurry else
                "Lighting too dark" if is_too_dark else
                "Lighting too bright" if is_too_bright else "Good quality"
            )
        }

    def detect_and_extract_feature(self, img: np.ndarray) -> Tuple[Optional[List[float]], Optional[List[int]], Dict[str, Any]]:
        """
        Detects primary face, extracts 128-d embedding, returns (embedding, [x, y, w, h], quality_info).
        """
        if img is None:
            return None, None, {"error": "Invalid image"}

        h, w = img.shape[:2]
        
        # Primary deep path: YuNet + SFace
        if self.detector is not None and self.recognizer is not None:
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(img)
            
            if faces is not None and len(faces) > 0:
                # Find face with highest confidence score
                best_face = max(faces, key=lambda f: f[-1])
                x, y, fw, fh = int(best_face[0]), int(best_face[1]), int(best_face[2]), int(best_face[3])
                bbox = [max(0, x), max(0, y), fw, fh]
                
                # Align and crop face using 5 facial landmarks
                aligned_face = self.recognizer.alignCrop(img, best_face)
                feature = self.recognizer.feature(aligned_face) # 128-d vector
                
                # Normalize vector to unit length
                feat_norm = feature / (np.linalg.norm(feature) + 1e-7)
                embedding_list = [float(v) for v in feat_norm.flatten()]
                
                quality = self.assess_quality(img, bbox)
                quality["confidence"] = round(float(best_face[-1]), 3)
                return embedding_list, bbox, quality

        # Fallback path if deep detector found no face or is missing
        if self.haar_cascade is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            haar_faces = self.haar_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            if len(haar_faces) > 0:
                x, y, fw, fh = haar_faces[0]
                bbox = [int(x), int(y), int(fw), int(fh)]
                # Produce a fallback normalized feature from resized face patch
                face_roi = cv2.resize(gray[y:y+fh, x:x+fw], (16, 8)).flatten().astype(np.float32)
                face_roi = face_roi / (np.linalg.norm(face_roi) + 1e-7)
                quality = self.assess_quality(img, bbox)
                quality["confidence"] = 0.70
                return [float(v) for v in face_roi], bbox, quality

        return None, None, {"error": "No face detected"}

    def detect_all_faces(self, img: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detects all faces in frame and extracts embeddings and bounding boxes for multi-face scanning.
        """
        results = []
        if img is None:
            return results

        h, w = img.shape[:2]
        if self.detector is not None and self.recognizer is not None:
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(img)
            if faces is not None:
                for face in faces:
                    score = float(face[-1])
                    if score < 0.5:
                        continue
                    x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    bbox = [max(0, x), max(0, y), fw, fh]
                    aligned_face = self.recognizer.alignCrop(img, face)
                    feature = self.recognizer.feature(aligned_face)
                    feat_norm = feature / (np.linalg.norm(feature) + 1e-7)
                    embedding = [float(v) for v in feat_norm.flatten()]
                    results.append({
                        "bbox": bbox,
                        "embedding": embedding,
                        "detection_score": round(score, 3)
                    })
        return results

    def match_student(self, query_embedding: List[float], enrolled_students: List[Dict[str, Any]], threshold: float = 0.363) -> Optional[Dict[str, Any]]:
        """
        Computes cosine similarity between query face and all enrolled students.
        Returns the best matching student with calculated confidence percentage.
        """
        if not query_embedding or not enrolled_students:
            return None

        query_vec = np.array(query_embedding, dtype=np.float32)
        best_match = None
        best_similarity = -1.0

        for student in enrolled_students:
            db_embedding = student.get("embedding")
            if not db_embedding:
                continue
            
            db_vec = np.array(db_embedding, dtype=np.float32)
            if len(query_vec) != len(db_vec):
                continue

            # SFace match cosine distance
            sim = float(np.dot(query_vec, db_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(db_vec) + 1e-7))
            
            if sim > best_similarity:
                best_similarity = sim
                best_match = student

        if best_match and best_similarity >= threshold:
            # Calibrate cosine score (~0.36 to 0.70) to intuitive percentage (70% - 99%)
            conf_percent = min(99.5, max(65.0, 65.0 + (best_similarity - threshold) * 100.0))
            return {
                "student_id": best_match["id"],
                "name": best_match["name"],
                "roll_number": best_match["roll_number"],
                "class_name": best_match.get("class_name", ""),
                "department": best_match.get("department", ""),
                "similarity_score": round(best_similarity, 4),
                "confidence_percentage": round(conf_percent, 1)
            }

        return None

# Singleton instance
face_engine = FaceEngine()
