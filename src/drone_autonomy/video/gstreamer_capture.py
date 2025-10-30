"""
Alternative: Use subprocess to capture GStreamer output as frames.
This bypasses OpenCV's GStreamer integration issues.
"""

import subprocess
import numpy as np
import cv2
import threading
import queue
import time
import os
from pathlib import Path

class GStreamerCapture:
    """Capture video from GStreamer pipeline using subprocess."""
    
    def __init__(self, pipeline, width=1920, height=1080):
        """
        Initialize GStreamer capture.
        
        Args:
            pipeline: GStreamer pipeline string
            width: Frame width
            height: Frame height
        """
        self.pipeline = pipeline
        self.width = width
        self.height = height
        self.frame_queue = queue.Queue(maxsize=2)
        self.process = None
        self.thread = None
        self.running = False
        self.gst_launch_path = self._find_gst_launch()
        
    def _find_gst_launch(self):
        """Find gst-launch-1.0 executable."""
        # Common GStreamer installation paths
        possible_paths = [
            r"C:\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe",
            r"C:\gstreamer\1.0\mingw_x86_64\bin\gst-launch-1.0.exe",
            r"C:\Program Files\GStreamer\1.0\bin\gst-launch-1.0.exe",
        ]
        
        # Check if it's in PATH
        import shutil
        gst_path = shutil.which("gst-launch-1.0")
        if gst_path:
            return gst_path
        
        # Check common locations
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return "gst-launch-1.0"  # Fallback, will likely fail
        
    def _read_frames(self):
        """Read frames from GStreamer process."""
        frame_size = self.width * self.height * 3  # BGR = 3 bytes per pixel
        
        while self.running:
            try:
                # Read raw frame data
                raw_frame = self.process.stdout.read(frame_size)
                
                if len(raw_frame) != frame_size:
                    print(f"Warning: Expected {frame_size} bytes, got {len(raw_frame)}")
                    continue
                
                # Convert to numpy array
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((self.height, self.width, 3))
                
                # Add to queue (drop old frames if full)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                
                self.frame_queue.put(frame)
                
            except Exception as e:
                if self.running:
                    print(f"Error reading frame: {e}")
                break
    
    def start(self):
        """Start GStreamer capture."""
        # Modify pipeline to output raw video to stdout
        pipeline_with_output = self.pipeline.replace(
            "appsink", 
            f"videoconvert ! video/x-raw,format=BGR,width={self.width},height={self.height} ! fdsink"
        )
        
        print(f"Starting GStreamer pipeline...")
        print(f"GStreamer executable: {self.gst_launch_path}")
        print(f"Pipeline: {pipeline_with_output[:80]}...")
        
        try:
            self.process = subprocess.Popen(
                [self.gst_launch_path, '-q'] + pipeline_with_output.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self.width * self.height * 3
            )
            
            self.running = True
            self.thread = threading.Thread(target=self._read_frames, daemon=True)
            self.thread.start()
            
            # Wait a moment for stream to start
            time.sleep(2)
            
            print("✓ GStreamer process started")
            return True
            
        except Exception as e:
            print(f"✗ Failed to start GStreamer: {e}")
            return False
    
    def read(self):
        """
        Read a frame.
        
        Returns:
            Tuple of (success, frame)
        """
        try:
            frame = self.frame_queue.get(timeout=1.0)
            return True, frame
        except queue.Empty:
            return False, None
    
    def isOpened(self):
        """Check if capture is running."""
        return self.running and self.process and self.process.poll() is None
    
    def release(self):
        """Stop capture and cleanup."""
        self.running = False
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None
        
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
        
        print("✓ GStreamer capture released")


# Test the wrapper
if __name__ == '__main__':
    pipeline = "rtspsrc location=rtsp://192.168.1.231:8554/1 latency=0 udp-reconnect=1 timeout=0 do-retransmission=false ! application/x-rtp ! decodebin3 ! queue max-size-buffers=1 leaky=2 ! videoconvert ! appsink sync=false"
    
    print("Testing GStreamerCapture wrapper...")
    print()
    
    cap = GStreamerCapture(pipeline, width=1920, height=1080)
    
    if cap.start():
        print("Waiting for frames...")
        time.sleep(3)
        
        frame_count = 0
        for i in range(30):
            ret, frame = cap.read()
            if ret:
                frame_count += 1
                if frame_count == 1:
                    print(f"✓ First frame received! Shape: {frame.shape}")
                    cv2.imwrite('test_frame_subprocess.jpg', frame)
                    print("✓ Saved test_frame_subprocess.jpg")
                    
                # Show frame
                cv2.imshow('GStreamer Stream', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print(f"Frame {i}: No frame available")
            
            time.sleep(0.033)  # ~30 FPS
        
        print(f"\n✓ Successfully read {frame_count} frames")
        
        cap.release()
        cv2.destroyAllWindows()
    else:
        print("✗ Failed to start capture")
