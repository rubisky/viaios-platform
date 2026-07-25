"""Data Enricher — generates realistic demo data for VIAIOS."""
import logging
import random
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DataEnricher:
    """Generates enriched demo data for all service modules."""

    LOCATIONS = ["Building A - Main Entrance", "Building B - Parking Lot", "Gate 1 - Vehicle Entry",
                 "Gate 2 - Pedestrian", "Warehouse C - Loading Dock", "Perimeter Fence - North",
                 "Lobby - Reception", "Elevator Bank - Floor 3", "Server Room", "Archive Room"]

    CAMERA_NAMES = ["Main Entrance HD", "Parking Lot PTZ", "Vehicle Gate LPR", "Pedestrian Gate",
                    "Loading Dock Wide", "North Perimeter", "Reception Desk", "Elevator 3F",
                    "Server Room Thermal", "Archive Fisheye", "Stairwell A", "Roof Access"]

    ALARM_TYPES = ["intrusion", "loitering", "crowd_gathering", "object_left", "speed_violation",
                   "wrong_direction", "restricted_area", "tamper_detection", "camera_offline",
                   "low_light", "motion_detected", "face_match", "plate_match"]

    CASE_TITLES = ["Warehouse theft investigation", "Parking lot hit-and-run", "Building A unauthorized access",
                   "Loading dock inventory discrepancy", "Perimeter fence breach attempt", "Lobby suspicious person",
                   "Elevator vandalism", "Server room access anomaly"]

    def generate_events(self, hours: int = 24) -> List[Dict]:
        """Generate timeline of analysis events."""
        events = []
        now = datetime.now(timezone.utc)
        for i in range(random.randint(20, 50)):
            t = now - timedelta(hours=random.randint(0, hours), minutes=random.randint(0, 59))
            obj_type = random.choice(["person", "vehicle", "bicycle", "animal", "object"])
            events.append({
                "id": str(uuid.uuid4())[:8],
                "camera": random.choice(self.CAMERA_NAMES),
                "type": f"{obj_type}_detected",
                "label": f"{obj_type.title()} #{random.randint(1, 999)}",
                "confidence": round(random.uniform(0.7, 0.99), 2),
                "timestamp": t.isoformat(),
                "location": random.choice(self.LOCATIONS),
            })
        return sorted(events, key=lambda e: e["timestamp"], reverse=True)

    def generate_alarms(self, count: int = 8) -> List[Dict]:
        """Generate realistic alarm events."""
        alarms = []
        now = datetime.now(timezone.utc)
        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for i in range(count):
            t = now - timedelta(hours=random.randint(0, 48), minutes=random.randint(0, 59))
            severity = random.choices(severities, weights=[1, 2, 4, 3])[0]
            alarm_type = random.choice(self.ALARM_TYPES)
            alarms.append({
                "id": f"alm-{uuid.uuid4().hex[:8]}",
                "type": alarm_type,
                "severity": severity,
                "camera": random.choice(self.CAMERA_NAMES),
                "location": random.choice(self.LOCATIONS),
                "message": f"{alarm_type.replace('_', ' ').title()} detected at {random.choice(self.LOCATIONS)}",
                "status": random.choice(["TRIGGERED", "ACKNOWLEDGED", "RESOLVED"]) if random.random() > 0.3 else "TRIGGERED",
                "createdAt": t.isoformat(),
            })
        return sorted(alarms, key=lambda a: a["createdAt"], reverse=True)

    def generate_trajectory(self, points: int = 15) -> List[Dict]:
        """Generate a realistic movement trajectory."""
        base_lat, base_lng = 31.2304, 121.4737
        path = []
        now = datetime.now(timezone.utc)
        for i in range(points):
            t = now - timedelta(minutes=(points - i) * 3)
            camera = random.choice(self.CAMERA_NAMES[:8])
            path.append({
                "id": f"pt-{i:03d}",
                "cameraId": f"cam-{self.CAMERA_NAMES.index(camera):03d}" if camera in self.CAMERA_NAMES else "cam-001",
                "cameraName": camera,
                "latitude": base_lat + random.uniform(-0.01, 0.01),
                "longitude": base_lng + random.uniform(-0.01, 0.01),
                "timestamp": t.isoformat(),
                "confidence": round(random.uniform(0.7, 0.99), 2),
            })
        return path

    def generate_cases(self, count: int = 5) -> List[Dict]:
        """Generate investigation cases."""
        cases = []
        now = datetime.now(timezone.utc)
        for i in range(count):
            t = now - timedelta(days=random.randint(0, 7))
            cases.append({
                "id": str(uuid.uuid4()),
                "title": self.CASE_TITLES[i % len(self.CASE_TITLES)],
                "description": f"Investigation into {self.CASE_TITLES[i].lower()} reported on {(t - timedelta(hours=random.randint(1,24))).strftime('%Y-%m-%d')}",
                "status": random.choice(["OPEN", "IN_PROGRESS", "CLOSED"]),
                "priority": random.choice(["P0", "P1", "P2", "P3"]),
                "createdAt": t.isoformat(),
            })
        return cases

    def get_all_data(self) -> Dict[str, Any]:
        return {
            "events": self.generate_events(),
            "alarms": self.generate_alarms(8),
            "trajectory": self.generate_trajectory(),
            "cases": self.generate_cases(5),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


data_enricher = DataEnricher()
