"""Prompt OS — Template Engine with Version Management and A/B Routing."""
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class PromptTemplate:
    """A managed prompt template with versioning."""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    template: str = ""           # Template string with {variable} placeholders
    variables: List[str] = field(default_factory=list)
    category: str = "general"    # general, analysis, search, report, alarm
    tags: List[str] = field(default_factory=list)
    status: str = "draft"
    usage_count: int = 0
    avg_score: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


BUILTIN_TEMPLATES = {
    "video_analysis": PromptTemplate(
        name="video_analysis",
        description="Analyze video footage for security incidents",
        version="1.0.0",
        template="""You are a video analysis expert. Analyze the following scene:
Camera: {camera_name}
Time: {time_range}
Task: {task_description}

Focus on:
1. Identify all persons, vehicles, and objects
2. Detect suspicious behavior or anomalies
3. Provide confidence scores for each detection
4. Recommend follow-up actions

Respond in JSON format with keys: detections, summary, recommendations.""",
        variables=["camera_name", "time_range", "task_description"],
        category="analysis", tags=["video", "security", "detection"],
        status="active",
    ),
    "target_search": PromptTemplate(
        name="target_search",
        description="Search for a specific target across cameras",
        version="1.0.0",
        template="""You are a search specialist. Find the following target:
Target: {target_description}
Time range: {time_range}
Location area: {location}

Search strategy:
1. Parse the description into searchable attributes
2. Query vector indices for matching persons/vehicles
3. Cross-reference with camera timestamps
4. Rank results by confidence and recency

Return results with: matches, confidence, camera, timestamp.""",
        variables=["target_description", "time_range", "location"],
        category="search", tags=["search", "target", "tracking"],
        status="active",
    ),
    "case_report": PromptTemplate(
        name="case_report",
        description="Generate an investigation case report",
        version="1.0.0",
        template="""Generate a professional investigation report for:
Case ID: {case_id}
Title: {case_title}
Evidence count: {evidence_count}
Key findings: {findings}

Report structure:
1. Executive Summary
2. Timeline of Events
3. Evidence Analysis
4. Suspect Identification
5. Conclusions and Recommendations

Format the report in markdown with clear sections.""",
        variables=["case_id", "case_title", "evidence_count", "findings"],
        category="report", tags=["report", "case", "investigation"],
        status="active",
    ),
    "alarm_evaluation": PromptTemplate(
        name="alarm_evaluation",
        description="Evaluate an alarm for false positive risk",
        version="1.0.0",
        template="""Evaluate this alarm for urgency and false positive risk:
Alarm Type: {alarm_type}
Severity: {severity}
Location: {location}
Time: {alarm_time}
Rule triggered: {rule_name}

Analysis:
1. Assess the likelihood of this being a real threat (0-100%)
2. Check for known false positive patterns
3. Recommend immediate actions
4. Suggest rule adjustments if needed

Return JSON: urgency_score, false_positive_risk, actions, rule_adjustments.""",
        variables=["alarm_type", "severity", "location", "alarm_time", "rule_name"],
        category="alarm", tags=["alarm", "evaluation", "triage"],
        status="active",
    ),
    "system_summary": PromptTemplate(
        name="system_summary",
        description="Generate a daily system operations summary",
        version="1.0.0",
        template="""Generate a daily system operations summary:
Date: {date}
Cameras online: {cameras_online}
Alarms triggered: {alarms_count}
Cases active: {cases_active}
Analysis tasks: {tasks_count}

Include:
1. System health overview
2. Notable events and alerts
3. Performance metrics
4. Recommendations for tomorrow

Format as a concise operational report.""",
        variables=["date", "cameras_online", "alarms_count", "cases_active", "tasks_count"],
        category="report", tags=["report", "summary", "operations"],
        status="active",
    ),
}


class PromptEngine:
    """Manages prompt templates with versioning, rendering, and A/B routing."""

    def __init__(self):
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}  # name -> {version -> template}
        self._active: Dict[str, str] = {}  # name -> active version
        self._history: List[Dict] = []
        self._ab_tests: Dict[str, Dict] = {}

        # Load builtin templates
        for tmpl in BUILTIN_TEMPLATES.values():
            self.register(tmpl)

    def register(self, template: PromptTemplate) -> str:
        """Register a prompt template."""
        if template.name not in self._templates:
            self._templates[template.name] = {}
        self._templates[template.name][template.version] = template
        if template.status == "active" and template.name not in self._active:
            self._active[template.name] = template.version
        logger.info("Registered prompt: %s v%s", template.name, template.version)
        return template.template_id

    def render(self, name: str, variables: Dict[str, Any], version: Optional[str] = None) -> str:
        """Render a template with variables."""
        ver = version or self._active.get(name)
        if not ver or name not in self._templates or ver not in self._templates[name]:
            # Return a basic prompt if template not found
            return f"Task: {name}\n\nContext: {json.dumps(variables, indent=2)}"

        tmpl = self._templates[name][ver]
        result = tmpl.template
        for var_name, var_value in variables.items():
            result = result.replace(f"{{{var_name}}}", str(var_value))

        tmpl.usage_count += 1
        self._history.append({
            "template": name, "version": ver, "variables": list(variables.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return result

    def route(self, task_type: str, variables: Dict[str, Any]) -> str:
        """Intelligent routing: select the best template for the task."""
        # A/B test active?
        if task_type in self._ab_tests:
            ab = self._ab_tests[task_type]
            import random
            version = ab["variant_a"] if random.random() < 0.5 else ab["variant_b"]
            return self.render(task_type, variables, version)

        # Category-based routing
        category_map = {
            "analysis": "video_analysis", "search": "target_search",
            "investigation": "case_report", "alarm": "alarm_evaluation",
            "report": "system_summary",
        }
        matched = category_map.get(task_type, "video_analysis")
        return self.render(matched, variables)

    def create_ab_test(self, name: str, variant_a: str, variant_b: str):
        """Set up A/B testing between two prompt versions."""
        self._ab_tests[name] = {"variant_a": variant_a, "variant_b": variant_b, "started": datetime.now(timezone.utc).isoformat()}
        logger.info("A/B test created for %s: %s vs %s", name, variant_a, variant_b)

    def list_templates(self, category: Optional[str] = None) -> List[dict]:
        """List all registered templates."""
        result = []
        for versions in self._templates.values():
            for tmpl in versions.values():
                if category and tmpl.category != category:
                    continue
                result.append({"name": tmpl.name, "version": tmpl.version, "category": tmpl.category,
                               "status": tmpl.status, "variables": tmpl.variables,
                               "usage_count": tmpl.usage_count, "description": tmpl.description})
        return result

    def get_template(self, name: str, version: Optional[str] = None) -> Optional[dict]:
        ver = version or self._active.get(name)
        if name in self._templates and ver in self._templates[name]:
            return self._templates[name][ver].to_dict()
        return None

    def get_stats(self) -> dict:
        total = sum(len(v) for v in self._templates.values())
        return {"total_templates": total, "active_templates": len(self._active),
                "total_renders": len(self._history), "ab_tests": len(self._ab_tests)}


# Global singleton
prompt_engine = PromptEngine()
