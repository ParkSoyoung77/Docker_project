import cv2
import mediapipe as mp
import numpy as np

class BioDetector:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

    def get_landmarks(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            
            # 얼굴을 감싸는 박스 계산 (Bounding Box)
            all_x = [lm.x for lm in face_landmarks.landmark]
            all_y = [lm.y for lm in face_landmarks.landmark]
            
            bbox = {
                "x": min(all_x) * w,
                "y": min(all_y) * h,
                "w": (max(all_x) - min(all_x)) * w,
                "h": (max(all_y) - min(all_y)) * h
            }
            
            # 주요 포인트 랜드마크 (예: 눈, 코, 입 주변 일부)
            points = [{"x": lm.x * w, "y": lm.y * h} for lm in face_landmarks.landmark]
            
            return {"bbox": bbox, "points": points}
        return None