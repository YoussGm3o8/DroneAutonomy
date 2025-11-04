"""
Building Landmark-Based Target Description System

Provides precise target descriptions using building landmarks instead of GPS coordinates.
Supports 3D-relative positioning with decimeter precision.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class LandmarkType(Enum):
    """Building landmark types"""
    NORTH_FACE = "north_face"
    SOUTH_FACE = "south_face"
    EAST_FACE = "east_face"
    WEST_FACE = "west_face"
    DOOR = "door"
    WINDOW = "window"
    CORNER_NE = "corner_northeast"
    CORNER_NW = "corner_northwest"
    CORNER_SE = "corner_southeast"
    CORNER_SW = "corner_southwest"
    ROOF_EDGE = "roof_edge"
    GROUND_LEVEL = "ground_level"


@dataclass
class BuildingDimensions:
    """
    Building exterior dimensions
    
    Attributes:
        length_north_south: Building length in north-south direction (meters)
        width_east_west: Building width in east-west direction (meters)
        height: Building height from ground to roof (meters)
        door_locations: List of door positions (face, offset_meters)
        window_locations: List of window positions (face, offset_meters, height_meters)
    """
    length_north_south: float
    width_east_west: float
    height: float
    door_locations: List[Tuple[LandmarkType, float]] = None
    window_locations: List[Tuple[LandmarkType, float, float]] = None
    
    def __post_init__(self):
        if self.door_locations is None:
            self.door_locations = []
        if self.window_locations is None:
            self.window_locations = []


@dataclass
class TargetDescription:
    """
    Landmark-based target description with schema validation
    
    Attributes:
        target_id: Unique identifier
        color: Target color (e.g., "red", "blue", "green")
        primary_landmark: Primary reference landmark
        offset_horizontal: Horizontal offset from landmark (meters, ±0.1m precision)
        offset_vertical: Vertical offset from ground level (meters, ±0.1m precision)
        offset_perpendicular: Perpendicular distance from wall face (meters, ±0.1m precision)
        secondary_landmarks: Additional reference points for disambiguation
        confidence: Detection confidence (0-1)
        timestamp: Detection timestamp
    """
    target_id: str
    color: str
    primary_landmark: LandmarkType
    offset_horizontal: float  # Along wall/face
    offset_vertical: float  # Height above ground
    offset_perpendicular: float  # Distance from wall face
    secondary_landmarks: List[str] = None
    confidence: float = 1.0
    timestamp: str = ""
    
    def __post_init__(self):
        if self.secondary_landmarks is None:
            self.secondary_landmarks = []
        
        # Round to decimeter precision
        self.offset_horizontal = round(self.offset_horizontal, 1)
        self.offset_vertical = round(self.offset_vertical, 1)
        self.offset_perpendicular = round(self.offset_perpendicular, 1)
    
    def validate_schema(self) -> Tuple[bool, List[str]]:
        """
        Validate description schema
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate target_id
        if not self.target_id or not isinstance(self.target_id, str):
            errors.append("Invalid target_id: must be non-empty string")
        
        # Validate color
        valid_colors = ["red", "blue", "green", "yellow", "orange", "purple", "black", "white"]
        if self.color.lower() not in valid_colors:
            errors.append(f"Invalid color '{self.color}': must be one of {valid_colors}")
        
        # Validate landmark
        if not isinstance(self.primary_landmark, LandmarkType):
            errors.append(f"Invalid primary_landmark: must be LandmarkType enum")
        
        # Validate offsets (must be finite numbers)
        for field_name, value in [
            ('offset_horizontal', self.offset_horizontal),
            ('offset_vertical', self.offset_vertical),
            ('offset_perpendicular', self.offset_perpendicular)
        ]:
            if not isinstance(value, (int, float)) or not np.isfinite(value):
                errors.append(f"Invalid {field_name}: must be finite number")
        
        # Validate confidence
        if not 0 <= self.confidence <= 1:
            errors.append(f"Invalid confidence {self.confidence}: must be in [0, 1]")
        
        # Check for ambiguity (must have at least one secondary landmark for precision)
        if not self.secondary_landmarks:
            errors.append("Ambiguity risk: no secondary landmarks provided")
        
        return len(errors) == 0, errors
    
    def to_text(self) -> str:
        """
        Generate human-readable text description
        
        Returns:
            Text description string
        """
        landmark_name = self.primary_landmark.value.replace('_', ' ').title()
        
        text = f"Target {self.target_id} ({self.color}):\n"
        text += f"  Primary Landmark: {landmark_name}\n"
        text += f"  Position:\n"
        text += f"    - {abs(self.offset_horizontal):.1f}m {'right' if self.offset_horizontal > 0 else 'left'} along {landmark_name}\n"
        text += f"    - {self.offset_vertical:.1f}m above ground level\n"
        text += f"    - {self.offset_perpendicular:.1f}m from wall face\n"
        
        if self.secondary_landmarks:
            text += f"  Secondary References: {', '.join(self.secondary_landmarks)}\n"
        
        text += f"  Confidence: {self.confidence:.2f}\n"
        
        return text
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'target_id': self.target_id,
            'color': self.color,
            'primary_landmark': self.primary_landmark.value,
            'offset_horizontal_m': self.offset_horizontal,
            'offset_vertical_m': self.offset_vertical,
            'offset_perpendicular_m': self.offset_perpendicular,
            'secondary_landmarks': self.secondary_landmarks,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
        }


class LandmarkBasedDescriptionGenerator:
    """
    Generates landmark-based target descriptions from vision data
    """
    
    def __init__(self, building: BuildingDimensions, logger=None):
        """
        Initialize description generator
        
        Args:
            building: Building dimensions and landmarks
            logger: Logger instance
        """
        self.building = building
        self.logger = logger
        self.descriptions = []
    
    def generate_description(
        self,
        target_id: str,
        color: str,
        position_3d: Tuple[float, float, float],
        drone_position: Tuple[float, float, float],
        drone_heading: float,
        confidence: float = 1.0
    ) -> Optional[TargetDescription]:
        """
        Generate landmark-based description for target
        
        Args:
            target_id: Unique target identifier
            color: Target color
            position_3d: Target 3D position (x, y, z) relative to building origin
            drone_position: Drone 3D position (x, y, z)
            drone_heading: Drone heading in degrees (0=North, 90=East)
            confidence: Detection confidence
            
        Returns:
            TargetDescription or None if invalid
        """
        import logging
        from datetime import datetime
        
        logger = self.logger or logging.getLogger(__name__)
        
        try:
            # Determine which building face the target is on
            x, y, z = position_3d
            
            # Find closest face
            faces = [
                (LandmarkType.NORTH_FACE, abs(y - self.building.length_north_south)),
                (LandmarkType.SOUTH_FACE, abs(y)),
                (LandmarkType.EAST_FACE, abs(x - self.building.width_east_west)),
                (LandmarkType.WEST_FACE, abs(x)),
            ]
            
            primary_landmark, _ = min(faces, key=lambda f: f[1])
            
            # Calculate offsets based on face
            if primary_landmark == LandmarkType.NORTH_FACE:
                offset_horizontal = x  # Distance along north face from west corner
                offset_perpendicular = self.building.length_north_south - y
            elif primary_landmark == LandmarkType.SOUTH_FACE:
                offset_horizontal = x
                offset_perpendicular = y
            elif primary_landmark == LandmarkType.EAST_FACE:
                offset_horizontal = y
                offset_perpendicular = self.building.width_east_west - x
            else:  # WEST_FACE
                offset_horizontal = y
                offset_perpendicular = x
            
            offset_vertical = z  # Height above ground
            
            # Find secondary landmarks for disambiguation
            secondary_landmarks = []
            
            # Check proximity to doors
            for door_face, door_offset in self.building.door_locations:
                if door_face == primary_landmark:
                    distance = abs(offset_horizontal - door_offset)
                    if distance < 2.0:  # Within 2m of door
                        direction = "right" if offset_horizontal > door_offset else "left"
                        secondary_landmarks.append(f"{distance:.1f}m {direction} of door")
            
            # Check proximity to corners
            if offset_horizontal < 1.0:
                secondary_landmarks.append("near west corner")
            elif offset_horizontal > (self.building.width_east_west - 1.0):
                secondary_landmarks.append("near east corner")
            
            # Create description
            description = TargetDescription(
                target_id=target_id,
                color=color,
                primary_landmark=primary_landmark,
                offset_horizontal=offset_horizontal,
                offset_vertical=offset_vertical,
                offset_perpendicular=offset_perpendicular,
                secondary_landmarks=secondary_landmarks,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
            # Validate schema
            is_valid, errors = description.validate_schema()
            if not is_valid:
                logger.error(f"Description validation failed: {errors}")
                return None
            
            self.descriptions.append(description)
            logger.info(f"Generated description for {target_id}:")
            logger.info(description.to_text())
            
            return description
            
        except Exception as e:
            logger.error(f"Error generating description: {e}", exc_info=True)
            return None
    
    def export_to_file(self, filepath: Path) -> bool:
        """
        Export all descriptions to text file
        
        Args:
            filepath: Output file path
            
        Returns:
            True if successful, False otherwise
        """
        import logging
        
        logger = self.logger or logging.getLogger(__name__)
        
        try:
            with open(filepath, 'w') as f:
                f.write("TARGET DESCRIPTIONS - LANDMARK-BASED\n")
                f.write("=" * 80 + "\n\n")
                
                for desc in self.descriptions:
                    # Validate before export
                    is_valid, errors = desc.validate_schema()
                    if not is_valid:
                        f.write(f"[INVALID] {desc.target_id}: {errors}\n\n")
                        continue
                    
                    f.write(desc.to_text())
                    f.write("\n" + "-" * 80 + "\n\n")
            
            logger.info(f"Exported {len(self.descriptions)} descriptions to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting descriptions: {e}", exc_info=True)
            return False
    
    def export_to_json(self, filepath: Path) -> bool:
        """
        Export all descriptions to JSON file
        
        Args:
            filepath: Output JSON file path
            
        Returns:
            True if successful, False otherwise
        """
        import logging
        
        logger = self.logger or logging.getLogger(__name__)
        
        try:
            data = {
                'building_dimensions': {
                    'length_north_south': self.building.length_north_south,
                    'width_east_west': self.building.width_east_west,
                    'height': self.building.height,
                },
                'targets': [desc.to_dict() for desc in self.descriptions]
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported {len(self.descriptions)} descriptions to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}", exc_info=True)
            return False
