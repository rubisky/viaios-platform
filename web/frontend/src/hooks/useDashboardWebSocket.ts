import { useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

interface UseDashboardWSProps {
  onAlarm?: (data: any) => void;
  onCameraChange?: (data: any) => void;
  onTaskComplete?: (data: any) => void;
}

export function useDashboardWebSocket({ onAlarm, onCameraChange, onTaskComplete }: UseDashboardWSProps = {}) {
  const { connected, subscribe } = useWebSocket('/ws/events');

  useEffect(() => {
    const unsubs: (() => void)[] = [];

    unsubs.push(subscribe('alarm', (data) => {
      onAlarm?.(data);
      // Fallback: refresh alarm count in Document title
      if (data.severity === 'high' || data.severity === 'critical') {
        document.title = `⚠ ${data.message || 'New Alarm'} — VIAIOS`;
        setTimeout(() => { document.title = 'VIAIOS — 智能视频侦查平台'; }, 3000);
      }
    }));

    unsubs.push(subscribe('notification', (_data) => {
      console.log('[WS] Notification received');
    }));

    unsubs.push(subscribe('heartbeat', () => {
      // Keep-alive, ignore
    }));

    // Wildcard handler for all events
    unsubs.push(subscribe('*', (data) => {
      const eventType = data.type || data.event || 'unknown';
      if (eventType === 'alarm' && data.severity === 'critical') {
        onAlarm?.(data);
      }
      if (eventType === 'camera_status') onCameraChange?.(data);
      if (eventType === 'task_complete') onTaskComplete?.(data);
    }));

    return () => unsubs.forEach(fn => fn());
  }, [subscribe, onAlarm, onCameraChange, onTaskComplete]);

  return { connected };
}
