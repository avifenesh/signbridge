"""Sign dictionary pipeline configuration."""

from pathlib import Path

# Directories
ROOT_DIR = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "output"
DATA_DIR = ROOT_DIR / "data"

# MediaPipe extraction
HAND_LANDMARKS = 21  # per hand
HAND_COUNT = 2
BODY_JOINTS = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist"]
FACE_PARAMS = ["eyebrows", "mouth", "head_tilt", "eye_gaze", "cheek_puff"]

TOTAL_HAND_POINTS = HAND_LANDMARKS * HAND_COUNT  # 42
TOTAL_BODY_POINTS = len(BODY_JOINTS)  # 6
TOTAL_FACE_PARAMS = len(FACE_PARAMS)  # 5
TOTAL_VALUES_PER_FRAME = TOTAL_HAND_POINTS + TOTAL_BODY_POINTS + TOTAL_FACE_PARAMS  # 53

# Hand landmark names (MediaPipe order)
HAND_LANDMARK_NAMES = [
    "wrist", "thumb_cmc", "thumb_mcp", "thumb_ip", "thumb_tip",
    "index_mcp", "index_pip", "index_dip", "index_tip",
    "middle_mcp", "middle_pip", "middle_dip", "middle_tip",
    "ring_mcp", "ring_pip", "ring_dip", "ring_tip",
    "pinky_mcp", "pinky_pip", "pinky_dip", "pinky_tip",
]

# Normalization
NORMALIZE_REFERENCE_JOINT = "right_shoulder"  # origin for normalization
NORMALIZE_SCALE_JOINTS = ("left_shoulder", "right_shoulder")  # distance = 1.0

# Keyframe selection
VELOCITY_THRESHOLD = 0.02  # minimum velocity change to register as keyframe
MIN_KEYFRAME_INTERVAL_MS = 33  # ~30fps minimum
MAX_KEYFRAME_INTERVAL_MS = 200  # force a keyframe at least every 200ms

# Avatar rendering targets
TARGET_FPS = 30
MIN_SIGN_DURATION_MS = 200
MAX_SIGN_DURATION_MS = 3000

# Dictionary
DICTIONARY_FILE = OUTPUT_DIR / "dictionary.json"
MAX_FRAMES_PER_SIGN = 60  # 2 seconds at 30fps
MIN_FRAMES_PER_SIGN = 3

# Quality validation
QUALITY_MIN_SCORE = 3  # 1-5 scale, minimum to include in V1
JOINT_POSITION_RANGE = (-2.0, 2.0)  # normalized coordinate bounds

# Face expression values
FACE_EXPRESSION_VALUES = {
    "eyebrows": ["raised", "neutral", "furrowed"],
    "mouth": ["closed", "open_slight", "open_wide", "rounded", "smile", "frown"],
    "head_tilt": ["neutral", "forward", "back", "left", "right"],
    "eye_gaze": ["center", "up", "down", "left", "right"],
    "cheek_puff": ["neutral", "puffed"],
}
