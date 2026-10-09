"""
Trigger Engine Detectors
========================
Modular signal detectors for detecting high-intent "Why Now?" triggers.
"""

from app.trigger_engine.detectors.base import BaseDetector, DetectedSignal
from app.trigger_engine.detectors.hiring import GTMHiringDetector
from app.trigger_engine.detectors.funding import FundingDetector
from app.trigger_engine.detectors.product import ProductLaunchDetector
from app.trigger_engine.detectors.social import SocialDiscussionDetector
from app.trigger_engine.detectors.tech import TechStackDetector

__all__ = [
    "BaseDetector",
    "DetectedSignal",
    "GTMHiringDetector",
    "FundingDetector",
    "ProductLaunchDetector",
    "SocialDiscussionDetector",
    "TechStackDetector",
]

