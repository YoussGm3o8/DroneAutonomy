"""YOLO-based object detection with TensorRT optimization support."""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional
from ultralytics import YOLO


class YOLODetector:
    """
    YOLO-based object detector for obstacle detection.
    
    Supports TensorRT optimization for real-time inference on NVIDIA GPUs.
    """
    
    def __init__(self, config: dict):
        """
        Initialize YOLO detector.
        
        Args:
            config: Detection configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.device = config.get('device', 'cuda')
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        self.nms_threshold = config.get('nms_threshold', 0.4)
        self.classes = config.get('classes', None)
        self.imgsz = config.get('imgsz', 640)  # Input image size for inference
        
    def load_model(self) -> bool:
        """
        Load YOLO model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            model_path = self.config.get('yolo_model', 'yolov8n.pt')
            self.model = YOLO(model_path)
            
            # Export to TensorRT if enabled
            if self.config.get('use_tensorrt', False):
                try:
                    self.logger.info("Exporting model to TensorRT...")
                    self.model.export(format='engine', device=self.device)
                    # Load the TensorRT model
                    tensorrt_path = model_path.replace('.pt', '.engine')
                    self.model = YOLO(tensorrt_path)
                    self.logger.info(f"Loaded TensorRT optimized model: {tensorrt_path}")
                except Exception as e:
                    self.logger.warning(f"TensorRT export failed, using PyTorch model: {e}")
            else:
                self.logger.info(f"Loaded YOLO model: {model_path} on {self.device}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading YOLO model: {e}")
            return False
    
    def detect(self, frame: np.ndarray) -> Tuple[List[dict], float]:
        """
        Detect objects in a frame.
        
        Args:
            frame: Input BGR image
            
        Returns:
            Tuple of (detections, inference_time)
            Each detection is a dict with keys: class_name, confidence, bbox (x1, y1, x2, y2)
        """
        if self.model is None:
            self.logger.error("Model not loaded")
            return [], 0.0
        
        try:
            import time
            start_time = time.time()
            
            # Run inference with specified input size
            results = self.model(frame, conf=self.confidence_threshold, iou=self.nms_threshold, 
                               imgsz=self.imgsz, verbose=False)
            
            inference_time = time.time() - start_time
            
            # Parse results
            detections = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Get confidence and class
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]
                    
                    # Filter by classes if specified
                    if self.classes is None or class_name in self.classes:
                        detections.append({
                            'class_name': class_name,
                            'class_id': class_id,
                            'confidence': confidence,
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'center': (int((x1 + x2) / 2), int((y1 + y2) / 2))
                        })
            
            return detections, inference_time
            
        except Exception as e:
            self.logger.error(f"Error detecting objects: {e}")
            return [], 0.0
    
    def draw_detections(self, frame: np.ndarray, detections: List[dict]) -> np.ndarray:
        """
        Draw detection boxes on frame.
        
        Args:
            frame: Input BGR image
            detections: List of detections
            
        Returns:
            Frame with drawn detections
        """
        output = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            # Convert to integers (important for scaled coordinates)
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            class_name = det['class_name']
            confidence = det['confidence']
            
            # Draw bounding box
            cv2.rectangle(output, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(output, (x1, y1 - label_size[1] - 10), (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(output, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return output
