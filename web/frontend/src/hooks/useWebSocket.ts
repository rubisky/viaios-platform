import { useEffect, useRef, useCallback, useState } from 'react';

type MessageHandler = (data: any) => void;

interface WSState { connected: boolean; lastMessage: any | null; error: string | null; }

export function useWebSocket(url: string = '/ws/events') {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const reconnectRef = useRef<ReturnType<typeof setTimeout>>();
  const attemptsRef = useRef(0);
  const [state, setState] = useState<WSState>({ connected: false, lastMessage: null, error: null });

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}${url}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setState({ connected: true, lastMessage: null, error: null });
        if (reconnectRef.current) { clearTimeout(reconnectRef.current); reconnectRef.current = undefined; }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setState(prev => ({ ...prev, lastMessage: data }));
          const eventType = data.type || data.event || 'unknown';
          const handlers = handlersRef.current.get(eventType);
          if (handlers) handlers.forEach(h => h(data));
          // Also notify wildcard handlers
          const allHandlers = handlersRef.current.get('*');
          if (allHandlers) allHandlers.forEach(h => h(data));
        } catch { /* ignore non-JSON messages */ }
      };

      ws.onerror = () => { /* silently ignore */ };
      ws.onclose = () => {
        setState(prev => ({ ...prev, connected: false }));
        // Stop retrying after 3 attempts
        if (attemptsRef.current < 3) {
          attemptsRef.current += 1;
          reconnectRef.current = setTimeout(() => connect(), 10000);
        }
      };
    } catch (e) {
      attemptsRef.current += 1;
      if (attemptsRef.current < 3) {
        reconnectRef.current = setTimeout(() => connect(), 15000);
      }
    }
  }, [url]);

  const subscribe = useCallback((eventType: string, handler: MessageHandler) => {
    if (!handlersRef.current.has(eventType)) handlersRef.current.set(eventType, new Set());
    handlersRef.current.get(eventType)!.add(handler);
    return () => { handlersRef.current.get(eventType)?.delete(handler); };
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify(data));
  }, []);

  useEffect(() => { connect(); return () => { wsRef.current?.close(); if (reconnectRef.current) clearTimeout(reconnectRef.current); }; }, [connect]);

  return { ...state, subscribe, send };
}
