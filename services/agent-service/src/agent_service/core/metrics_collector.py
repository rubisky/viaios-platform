"""System Metrics Collector — gathers CPU, memory, disk, network stats."""
import os
import time
import json
import threading
from datetime import datetime, timezone

class SystemMetrics:
    """Collects and caches system performance metrics."""

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

    def _collect_loop(self):
        while self._running:
            try:
                metrics = {}
                # CPU
                try:
                    with open('/proc/stat') as f:
                        cpu = f.readline().split()
                        if len(cpu) >= 5:
                            total = sum(int(x) for x in cpu[1:])
                            idle = int(cpu[4])
                            metrics['cpu_percent'] = round((1 - idle / total) * 100, 1)
                except: metrics['cpu_percent'] = 0

                # Memory
                try:
                    with open('/proc/meminfo') as f:
                        lines = f.readlines()
                        mem = {}
                        for line in lines[:5]:
                            parts = line.split(':')
                            if len(parts) == 2:
                                key = parts[0].strip()
                                val = int(parts[1].strip().split()[0])
                                mem[key] = val
                        total = mem.get('MemTotal', 1)
                        available = mem.get('MemAvailable', 0)
                        metrics['memory_total_mb'] = round(total / 1024, 0)
                        metrics['memory_used_mb'] = round((total - available) / 1024, 0)
                        metrics['memory_percent'] = round((1 - available / total) * 100, 1)
                except: pass

                # Disk
                try:
                    stat = os.statvfs('/')
                    total = stat.f_frsize * stat.f_blocks
                    free = stat.f_frsize * stat.f_bavail
                    metrics['disk_total_gb'] = round(total / 1e9, 1)
                    metrics['disk_free_gb'] = round(free / 1e9, 1)
                    metrics['disk_percent'] = round((1 - free / total) * 100, 1)
                except: pass

                # Network
                try:
                    with open('/proc/net/dev') as f:
                        for line in f:
                            if 'eth0' in line or 'ens' in line:
                                parts = line.split()
                                metrics['net_rx_mb'] = round(int(parts[1]) / 1e6, 2)
                                metrics['net_tx_mb'] = round(int(parts[9]) / 1e6, 2)
                                break
                except: pass

                # Process count
                try:
                    metrics['process_count'] = len(os.listdir('/proc')) - len([p for p in os.listdir('/proc') if not p.isdigit()])
                except: metrics['process_count'] = 0

                metrics['timestamp'] = datetime.now(timezone.utc).isoformat()
                with self._lock:
                    self._cache = metrics
            except Exception:
                pass
            time.sleep(5)

    def get_metrics(self) -> dict:
        with self._lock:
            return dict(self._cache)

    def stop(self):
        self._running = False


# Global singleton
system_metrics = SystemMetrics()


def get_system_metrics() -> dict:
    """Get the latest system metrics snapshot."""
    return system_metrics.get_metrics()
