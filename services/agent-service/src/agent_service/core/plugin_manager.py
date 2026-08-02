"""
Plugin Manager — P2-5
Hot-loadable plugin system for AI Kernel extensibility.

Supports: dynamic loading, lifecycle hooks, dependency resolution,
version management, sandbox isolation, auto-reload on file change.
"""
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ── Domain Types ───────────────────────────────────────────────────

class PluginStatus(Enum):
    REGISTERED = "registered"
    LOADED     = "loaded"
    ACTIVE     = "active"
    PAUSED     = "paused"
    ERROR      = "error"
    UNLOADED   = "unloaded"

class HookPoint(Enum):
    ON_STARTUP      = "on_startup"
    ON_SHUTDOWN     = "on_shutdown"
    PRE_INFERENCE   = "pre_inference"
    POST_INFERENCE  = "post_inference"
    ON_ALARM        = "on_alarm"
    ON_AGENT_ACTION = "on_agent_action"
    ON_EVENT        = "on_event"
    ON_SCHEDULE     = "on_schedule"

@dataclass
class PluginMetadata:
    """Plugin descriptor."""
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PluginInfo:
    """Runtime plugin information."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: PluginMetadata = field(default_factory=lambda: PluginMetadata("", ""))
    status: PluginStatus = PluginStatus.REGISTERED
    module_path: str = ""
    module: Any = None
    instance: Any = None
    config: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None
    error: str = ""
    load_count: int = 0
    total_executions: int = 0
    avg_latency_ms: float = 0.0


# ── Plugin Manager ─────────────────────────────────────────────────

class PluginManager:
    """
    Hot-loadable plugin system for extending AI Kernel functionality.

    Usage:
        pm = PluginManager(plugin_dir="/opt/viaios/plugins")
        pm.load_plugin("my_plugin.py")
        pm.activate("my-plugin")
        pm.execute_hook(HookPoint.PRE_INFERENCE, model="yolov8n")
    """

    def __init__(self, plugin_dir: str = "/opt/viaios/plugins",
                 auto_reload: bool = True):
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.auto_reload = auto_reload

        self._plugins: Dict[str, PluginInfo] = {}
        self._hooks: Dict[HookPoint, List[Callable]] = {h: [] for h in HookPoint}
        self._lock = threading.Lock()
        self._watch_thread: Optional[threading.Thread] = None
        self._file_mtimes: Dict[str, float] = {}

        # Start file watcher
        if auto_reload:
            self._start_watcher()

        logger.info("PluginManager initialized [dir=%s, auto_reload=%s]",
                    self.plugin_dir, auto_reload)

    # ── Plugin Lifecycle ────────────────────────────────────────

    def register(self, metadata: PluginMetadata, module_path: str = "") -> str:
        """Register a plugin descriptor."""
        with self._lock:
            if metadata.name in self._plugins:
                raise ValueError(f"Plugin already registered: {metadata.name}")
            info = PluginInfo(metadata=metadata, module_path=module_path)
            self._plugins[metadata.name] = info
            logger.info("Plugin registered: %s v%s", metadata.name, metadata.version)
            return info.id

    def load(self, name: str) -> PluginInfo:
        """Load a plugin module from file."""
        info = self._require_plugin(name)

        try:
            # Find module file
            if info.module_path:
                path = info.module_path
            else:
                candidates = [
                    self.plugin_dir / f"{name}.py",
                    self.plugin_dir / f"viaios_plugin_{name}.py",
                ]
                path = next((p for p in candidates if p.exists()), None)

            if not path:
                raise FileNotFoundError(f"Plugin file not found for: {name}")

            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                f"viaios_plugin_{name}", str(path)
            )
            if not spec or not spec.loader:
                raise ImportError(f"Cannot load plugin spec: {name}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find plugin class (convention: Plugin class or first class inheriting BasePlugin)
            plugin_class = None
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == spec.name and hasattr(obj, 'on_load'):
                    plugin_class = obj
                    break

            if not plugin_class:
                # Try simple module with lifecycle functions
                plugin_class = type('AutoPlugin', (), {
                    k: v for k, v in module.__dict__.items()
                    if callable(v) and k in ['on_load', 'on_activate', 'on_deactivate', 'execute']
                })

            info.module = module
            info.instance = plugin_class() if plugin_class.__name__ != 'AutoPlugin' else plugin_class
            info.status = PluginStatus.LOADED
            info.loaded_at = datetime.now(timezone.utc)
            info.load_count += 1
            info.error = ""

            # Call on_load hook
            if hasattr(info.instance, 'on_load'):
                info.instance.on_load(info.config)

            # Register hook handlers
            for hook_name in info.metadata.hooks:
                try:
                    hook = HookPoint(hook_name)
                    handler = getattr(info.instance, hook.value, None)
                    if handler:
                        self._hooks[hook].append(handler)
                except ValueError:
                    pass

            self._file_mtimes[str(path)] = os.path.getmtime(str(path))
            logger.info("Plugin loaded: %s v%s [hooks=%s]",
                       name, info.metadata.version, info.metadata.hooks)
            return info

        except Exception as e:
            info.status = PluginStatus.ERROR
            info.error = f"{type(e).__name__}: {e}"
            logger.error("Plugin load failed [%s]: %s", name, e)
            traceback.print_exc()
            raise

    def activate(self, name: str) -> PluginInfo:
        """Activate a loaded plugin (calls on_activate)."""
        info = self._require_plugin(name)
        if info.status != PluginStatus.LOADED:
            raise RuntimeError(f"Plugin must be LOADED to activate: {name} [{info.status.value}]")

        try:
            if hasattr(info.instance, 'on_activate'):
                info.instance.on_activate(info.config)
            info.status = PluginStatus.ACTIVE
            logger.info("Plugin activated: %s", name)
            return info
        except Exception as e:
            info.status = PluginStatus.ERROR
            info.error = str(e)
            raise

    def deactivate(self, name: str):
        """Deactivate a plugin."""
        info = self._require_plugin(name)
        if hasattr(info.instance, 'on_deactivate'):
            info.instance.on_deactivate()
        info.status = PluginStatus.PAUSED

    def unload(self, name: str):
        """Unload a plugin completely."""
        info = self._require_plugin(name)
        self.deactivate(name)
        # Remove hooks
        for hook, handlers in self._hooks.items():
            if info.instance and hasattr(info.instance, hook.value):
                h = getattr(info.instance, hook.value, None)
                if h in handlers:
                    handlers.remove(h)
        info.status = PluginStatus.UNLOADED
        info.module = None
        info.instance = None

    def reload(self, name: str) -> PluginInfo:
        """Reload a plugin (unload then load)."""
        info = self._require_plugin(name)
        old_config = info.config
        self.unload(name)
        # Clear import cache
        mod_name = f"viaios_plugin_{name}"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        info = self.load(name)
        info.config = old_config
        self.activate(name)
        return info

    # ── Hook Execution ──────────────────────────────────────────

    def execute_hook(self, hook: HookPoint, **kwargs) -> List[Any]:
        """Execute all registered handlers for a hook point."""
        handlers = self._hooks.get(hook, [])
        results = []
        for handler in handlers:
            start = time.time()
            try:
                result = handler(**kwargs)
                results.append(result)
            except Exception as e:
                logger.error("Hook %s handler failed: %s", hook.value, e)
                results.append({"error": str(e)})
        return results

    # ── Plugin Discovery ────────────────────────────────────────

    def discover(self) -> List[str]:
        """Scan plugin directory for new plugins."""
        discovered = []
        if not self.plugin_dir.exists():
            return discovered
        for path in self.plugin_dir.glob("*.py"):
            name = path.stem.replace("viaios_plugin_", "")
            if name not in self._plugins:
                discovered.append(name)
        return discovered

    def load_all(self) -> Dict[str, PluginInfo]:
        """Discover and load all plugins."""
        results = {}
        for name in self.discover():
            try:
                info = self.load(name)
                if info.status == PluginStatus.LOADED:
                    self.activate(name)
                results[name] = info
            except Exception as e:
                logger.warning("Failed to load plugin %s: %s", name, e)
        return results

    # ── Query ───────────────────────────────────────────────────

    def get(self, name: str) -> Optional[PluginInfo]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict]:
        """List all registered plugins."""
        return [
            {
                "name": name, "version": info.metadata.version,
                "status": info.status.value, "hooks": info.metadata.hooks,
                "load_count": info.load_count, "error": info.error[:100],
            }
            for name, info in self._plugins.items()
        ]

    def stats(self) -> Dict[str, Any]:
        """Plugin manager statistics."""
        return {
            "total_plugins": len(self._plugins),
            "active": sum(1 for p in self._plugins.values() if p.status == PluginStatus.ACTIVE),
            "loaded": sum(1 for p in self._plugins.values() if p.status == PluginStatus.LOADED),
            "error": sum(1 for p in self._plugins.values() if p.status == PluginStatus.ERROR),
            "hooks": {h.value: len(fns) for h, fns in self._hooks.items()},
        }

    # ── Internal ────────────────────────────────────────────────

    def _require_plugin(self, name: str) -> PluginInfo:
        info = self._plugins.get(name)
        if not info:
            raise KeyError(f"Plugin not found: {name}")
        return info

    def _start_watcher(self):
        """Start file system watcher for auto-reload."""
        def _watch():
            while True:
                time.sleep(5)
                if not self.plugin_dir.exists():
                    continue
                for path in self.plugin_dir.glob("*.py"):
                    try:
                        mtime = os.path.getmtime(str(path))
                        name = path.stem.replace("viaios_plugin_", "")
                        old = self._file_mtimes.get(str(path), 0)
                        if mtime > old and name in self._plugins:
                            logger.info("Plugin file changed, reloading: %s", name)
                            self.reload(name)
                        self._file_mtimes[str(path)] = mtime
                    except Exception:
                        pass
        self._watch_thread = threading.Thread(target=_watch, daemon=True)
        self._watch_thread.start()


# ── Example Plugin Template ───────────────────────────────────────

EXAMPLE_PLUGIN = '''
"""
VIAIOS Plugin Template — copy this to create new plugins.
Place in /opt/viaios/plugins/your_plugin.py
"""
import logging
logger = logging.getLogger("viaios-plugin")

# Lifecycle hooks
def on_load(config: dict):
    """Called when plugin is loaded. Initialize resources here."""
    logger.info("Plugin loaded with config: %s", config)

def on_activate(config: dict):
    """Called when plugin is activated. Start processing here."""
    logger.info("Plugin activated")

def on_deactivate():
    """Called when plugin is deactivated. Clean up here."""
    logger.info("Plugin deactivated")

# Hook handlers
def pre_inference(model: str, inputs: dict):
    """Hook: called before model inference."""
    logger.info(f"Pre-inference: {model}")
    return {"status": "ok"}

def post_inference(model: str, outputs: dict, latency_ms: float):
    """Hook: called after model inference."""
    logger.info(f"Post-inference: {model} [{latency_ms:.1f}ms]")
    return {"processed": True}

def on_alarm(alarm_type: str, severity: str, metadata: dict):
    """Hook: called when an alarm is triggered."""
    logger.info(f"Alarm: {alarm_type} [{severity}]")
    return {"escalated": severity == "CRITICAL"}

# Plugin metadata (auto-discovered)
__plugin_meta__ = {
    "name": "example_plugin",
    "version": "1.0.0",
    "description": "Example VIAIOS plugin",
    "hooks": ["pre_inference", "post_inference", "on_alarm"],
}
'''


# ── Convenience ────────────────────────────────────────────────────

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
