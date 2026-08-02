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


# ═══════════════════════════════════════════════════════════════════
# P1-3: Evaluation System
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PromptEvaluation:
    """Evaluation result for a rendered prompt."""
    eval_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    template_name: str = ""
    version: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    rendered_prompt: str = ""
    response: Optional[str] = None
    scores: Dict[str, float] = field(default_factory=dict)  # dimension → score
    overall_score: float = 0.0
    user_rating: Optional[int] = None   # 1-5 star
    feedback: str = ""
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PromptEvaluator:
    """
    Evaluate prompt effectiveness using automated metrics and user feedback.

    Dimensions:
    - clarity: Is the prompt clear and unambiguous?
    - specificity: Does it provide enough detail?
    - consistency: Does it produce consistent results?
    - effectiveness: Does the response match expectations?
    """

    def __init__(self):
        self._evaluations: List[PromptEvaluation] = []

    def evaluate(self, template: PromptTemplate, rendered: str,
                 response: Optional[str] = None) -> PromptEvaluation:
        """Auto-evaluate a rendered prompt."""
        ev = PromptEvaluation(
            template_name=template.name,
            version=template.version,
            rendered_prompt=rendered[:500],
            response=response[:500] if response else None,
        )

        # Automated scoring
        scores = {}

        # Clarity: prompts with clear instruction words score higher
        clarity_words = ["analyze", "identify", "describe", "explain", "return",
                        "generate", "compare", "summarize", "evaluate", "recommend"]
        clarity_count = sum(rendered.lower().count(w) for w in clarity_words)
        scores["clarity"] = min(1.0, clarity_count / 5)

        # Specificity: more structured prompts score higher
        structure_markers = ["step", "format", "include", "exclude", "section",
                            "requirements", "constraints", "output"]
        structure_count = sum(rendered.lower().count(w) for w in structure_markers)
        scores["specificity"] = min(1.0, structure_count / 4)

        # Length efficiency (not too short, not too long)
        length = len(rendered)
        if length < 100:
            scores["conciseness"] = 0.5
        elif length < 500:
            scores["conciseness"] = 0.9
        elif length < 1000:
            scores["conciseness"] = 0.8
        else:
            scores["conciseness"] = 0.6

        ev.scores = scores
        ev.overall_score = round(sum(scores.values()) / len(scores), 3)
        self._evaluations.append(ev)

        # Update template metrics
        template.avg_score = round(
            (template.avg_score * template.usage_count + ev.overall_score) / (template.usage_count + 1), 3
        )

        return ev

    def add_feedback(self, eval_id: str, rating: int, feedback: str = ""):
        """Add user feedback to an evaluation."""
        for ev in self._evaluations:
            if ev.eval_id == eval_id:
                ev.user_rating = rating
                ev.feedback = feedback
                break

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics."""
        if not self._evaluations:
            return {"total_evaluations": 0}
        scores = [ev.overall_score for ev in self._evaluations]
        ratings = [ev.user_rating for ev in self._evaluations if ev.user_rating]
        return {
            "total_evaluations": len(self._evaluations),
            "avg_score": round(sum(scores) / len(scores), 3),
            "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else 0,
            "rated_count": len(ratings),
        }


# ═══════════════════════════════════════════════════════════════════
# P1-3: Prompt Marketplace
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MarketPrompt:
    """A prompt listing in the marketplace."""
    listing_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    template: str = ""
    variables: List[str] = field(default_factory=list)
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    author: str = "system"
    version: str = "1.0"
    downloads: int = 0
    rating: float = 0.0
    reviews: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified: bool = False


class PromptMarketplace:
    """Community prompt sharing and discovery."""

    def __init__(self):
        self._listings: Dict[str, MarketPrompt] = {}
        self._categories = ["analysis", "search", "report", "alarm",
                           "video", "knowledge", "agent", "general"]

    def publish(self, prompt: MarketPrompt) -> str:
        """Publish a prompt to the marketplace."""
        self._listings[prompt.listing_id] = prompt
        logger.info("Prompt published to market: %s by %s", prompt.name, prompt.author)
        return prompt.listing_id

    def search(self, query: str = "", category: str = "",
               tags: List[str] = None, sort_by: str = "rating") -> List[Dict]:
        """Search the prompt marketplace."""
        results = list(self._listings.values())

        if query:
            q = query.lower()
            results = [p for p in results
                      if q in p.name.lower() or q in p.description.lower()
                      or any(q in t.lower() for t in p.tags)]
        if category:
            results = [p for p in results if p.category == category]
        if tags:
            results = [p for p in results
                      if any(t in p.tags for t in tags)]

        # Sort
        if sort_by == "rating":
            results.sort(key=lambda p: p.rating, reverse=True)
        elif sort_by == "downloads":
            results.sort(key=lambda p: p.downloads, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda p: p.created_at, reverse=True)

        return [
            {"listing_id": p.listing_id, "name": p.name, "description": p.description,
             "category": p.category, "tags": p.tags, "author": p.author,
             "rating": p.rating, "downloads": p.downloads, "verified": p.verified}
            for p in results[:20]
        ]

    def get_listing(self, listing_id: str) -> Optional[Dict]:
        """Get a full marketplace listing."""
        p = self._listings.get(listing_id)
        if p:
            p.downloads += 1
            return {"name": p.name, "description": p.description, "template": p.template,
                    "variables": p.variables, "category": p.category, "tags": p.tags,
                    "author": p.author, "version": p.version, "rating": p.rating}
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Marketplace statistics."""
        return {
            "total_listings": len(self._listings),
            "by_category": {c: sum(1 for p in self._listings.values() if p.category == c)
                          for c in self._categories},
            "verified_count": sum(1 for p in self._listings.values() if p.verified),
            "avg_rating": round(sum(p.rating for p in self._listings.values()) / max(len(self._listings), 1), 1),
        }


# ═══════════════════════════════════════════════════════════════════
# P1-3: Enhanced Prompt Engine (with auto-optimization)
# ═══════════════════════════════════════════════════════════════════

class ABTestResult:
    """Statistical A/B test result."""
    def __init__(self, name: str, variant_a: str, variant_b: str,
                 a_score: float, b_score: float, a_samples: int, b_samples: int):
        self.name = name
        self.variant_a = variant_a
        self.variant_b = variant_b
        self.a_score = a_score
        self.b_score = b_score
        self.a_samples = a_samples
        self.b_samples = b_samples
        self.winner = variant_b if b_score > a_score else variant_a
        self.improvement_pct = round(abs(b_score - a_score) / max(a_score, 0.01) * 100, 1)
        self.significant = (min(a_samples, b_samples) >= 5) and (abs(b_score - a_score) > 0.05)


# Enhanced PromptEngine with P1-3 features
class PromptEngineV2(PromptEngine):
    """Enhanced PromptEngine with evaluation, marketplace, and optimization."""

    def __init__(self):
        super().__init__()
        self.evaluator = PromptEvaluator()
        self.marketplace = PromptMarketplace()

        # Seed marketplace with builtin templates
        for tmpl in BUILTIN_TEMPLATES.values():
            self.marketplace.publish(MarketPrompt(
                name=tmpl.name, description=tmpl.description,
                template=tmpl.template, variables=tmpl.variables,
                category=tmpl.category, tags=tmpl.tags,
                verified=True,
            ))

    def render_and_evaluate(self, name: str, variables: Dict[str, Any],
                           response: Optional[str] = None) -> Dict[str, Any]:
        """Render a prompt and auto-evaluate it."""
        rendered = self.render(name, variables)
        tmpl_ver = self._active.get(name, "latest")
        tmpl = self._templates.get(name, {}).get(tmpl_ver)

        result = {"rendered": rendered}
        if tmpl:
            ev = self.evaluator.evaluate(tmpl, rendered, response)
            result["evaluation"] = {
                "eval_id": ev.eval_id,
                "scores": ev.scores,
                "overall_score": ev.overall_score,
            }
        return result

    def conclude_ab_test(self, name: str) -> Optional[Dict]:
        """Conclude an A/B test with statistical analysis."""
        ab = self._ab_tests.get(name)
        if not ab:
            return None

        # Collect evaluation data for both variants
        a_scores = [ev.overall_score for ev in self.evaluator._evaluations
                    if ev.version == ab["variant_a"]]
        b_scores = [ev.overall_score for ev in self.evaluator._evaluations
                    if ev.version == ab["variant_b"]]

        result = ABTestResult(
            name=name,
            variant_a=ab["variant_a"],
            variant_b=ab["variant_b"],
            a_score=round(sum(a_scores) / len(a_scores), 3) if a_scores else 0,
            b_score=round(sum(b_scores) / len(b_scores), 3) if b_scores else 0,
            a_samples=len(a_scores),
            b_samples=len(b_scores),
        )

        # Auto-select winner if significant
        if result.significant:
            self._active[name] = result.winner
            logger.info("A/B test %s concluded: winner=%s (%.1f%% improvement)",
                       name, result.winner, result.improvement_pct)

        del self._ab_tests[name]
        return {
            "name": name, "winner": result.winner,
            "a_score": result.a_score, "b_score": result.b_score,
            "improvement_pct": result.improvement_pct,
            "significant": result.significant,
        }

    def optimize_prompt(self, name: str) -> Optional[Dict]:
        """Suggest prompt optimizations based on evaluation data."""
        scores = [ev.scores for ev in self.evaluator._evaluations
                 if ev.template_name == name]

        if not scores:
            return None

        avg_scores = {}
        for dim in ["clarity", "specificity", "conciseness"]:
            vals = [s.get(dim, 0) for s in scores]
            avg_scores[dim] = round(sum(vals) / len(vals), 3)

        suggestions = []
        if avg_scores.get("clarity", 0) < 0.7:
            suggestions.append("Add clearer instruction verbs (analyze, describe, explain)")
        if avg_scores.get("specificity", 0) < 0.7:
            suggestions.append("Add more structure (steps, sections, format requirements)")
        if avg_scores.get("conciseness", 0) < 0.7:
            suggestions.append("Reduce prompt length or remove redundant instructions")

        return {
            "template": name,
            "current_scores": avg_scores,
            "suggestions": suggestions,
            "evaluation_count": len(scores),
        }


# Global singletons
prompt_engine = PromptEngineV2()
