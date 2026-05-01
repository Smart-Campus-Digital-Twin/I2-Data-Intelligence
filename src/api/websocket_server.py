"""
Member 3: Real-Time WebSocket & Data Broadcast Specialist
Requirement: REQ-I2-4
WebSocket server broadcasting energy forecasts, occupancy updates, and anomaly alerts.
"""

from fastapi import FastAPI, WebSocketException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import socketio
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Set
import redis.asyncio as redis
import uuid
from pydantic import BaseModel
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== Data Models ====================
class ForecastMessage(BaseModel):
    building_id: str
    timestamps: List[str]
    predicted_kw: List[float]
    confidence_lower: List[float]
    confidence_upper: List[float]
    average_kw: float
    peak_kw: float
    peak_hour: int
    model_version: str
    generated_at: str


class OccupancyUpdate(BaseModel):
    room_id: str
    building_id: str
    occupancy_count: int
    capacity: int
    classification: str  # 'low', 'medium', 'high', 'critical'
    confidence: float
    timestamp: str


class AnomalyAlert(BaseModel):
    alert_id: str
    alert_type: str  # 'z_score' or 'threshold'
    severity: str  # 'high', 'medium', 'low'
    sensor_id: str
    building_id: str
    room_id: str
    measured_value: float
    threshold_value: float
    message: str
    timestamp: str


class BroadcastMetrics(BaseModel):
    event_type: str
    namespace: str
    client_count: int
    data_size_bytes: int
    latency_ms: float
    timestamp: str


# ==================== WebSocket Manager ====================
class ConnectionManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict] = {}
        self.subscriptions: Dict[str, Set[str]] = {
            '/forecast': set(),
            '/occupancy': set(),
            '/anomalies': set()
        }
        self.message_buffer: Dict[str, List] = {
            '/forecast': [],
            '/occupancy': [],
            '/anomalies': []
        }
        self.max_buffer_size = 1000
        self.max_buffer_age_hours = 1
    
    async def connect(self, sid: str, namespace: str):
        """Register a new client connection."""
        self.active_connections[sid] = {
            'namespace': namespace,
            'connected_at': datetime.utcnow(),
            'last_heartbeat': datetime.utcnow(),
            'latencies': []
        }
        self.subscriptions[namespace].add(sid)
        logger.info(f"Client {sid} connected to {namespace}. Total: {len(self.active_connections)}")
    
    async def disconnect(self, sid: str):
        """Unregister a disconnected client."""
        if sid in self.active_connections:
            namespace = self.active_connections[sid]['namespace']
            del self.active_connections[sid]
            self.subscriptions[namespace].discard(sid)
            logger.info(f"Client {sid} disconnected. Remaining: {len(self.active_connections)}")
    
    async def broadcast(self, namespace: str, message: dict, redis_client=None):
        """Broadcast message to all clients in namespace."""
        start_time = datetime.utcnow()
        message_with_meta = {
            **message,
            'broadcast_timestamp': start_time.isoformat(),
            'broadcast_id': str(uuid.uuid4())
        }
        
        # Buffer message
        self._add_to_buffer(namespace, message_with_meta)
        
        # Get subscribed clients
        subscribers = self.subscriptions.get(namespace, set())
        data_size = len(json.dumps(message_with_meta).encode())
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        logger.info(f"Broadcasting to {len(subscribers)} clients in {namespace}. "
                   f"Size: {data_size}B, Latency: {latency_ms:.2f}ms")
        
        # Persist metrics
        if redis_client:
            await self._log_broadcast_metrics(
                redis_client, namespace, len(subscribers), data_size, latency_ms
            )
        
        return {
            'broadcast_id': message_with_meta['broadcast_id'],
            'client_count': len(subscribers),
            'data_size_bytes': data_size,
            'latency_ms': latency_ms
        }
    
    def _add_to_buffer(self, namespace: str, message: dict):
        """Add message to buffer for replay to reconnecting clients."""
        buffer = self.message_buffer[namespace]
        buffer.append({
            'data': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Trim buffer if too large
        if len(buffer) > self.max_buffer_size:
            buffer.pop(0)
    
    async def _log_broadcast_metrics(self, redis_client, namespace: str, 
                                    client_count: int, data_size: int, latency_ms: float):
        """Store broadcast metrics in Redis for monitoring."""
        metrics_key = f"broadcast_metrics:{namespace}:{datetime.utcnow().isoformat()}"
        metrics = {
            'namespace': namespace,
            'client_count': client_count,
            'data_size_bytes': data_size,
            'latency_ms': latency_ms,
            'timestamp': datetime.utcnow().isoformat()
        }
        await redis_client.setex(metrics_key, 3600, json.dumps(metrics))
    
    async def get_buffered_messages(self, namespace: str, limit: int = 50) -> List[dict]:
        """Return recent messages for client replay after reconnection."""
        buffer = self.message_buffer[namespace]
        return buffer[-limit:] if buffer else []
    
    def update_heartbeat(self, sid: str):
        """Update client's last heartbeat timestamp."""
        if sid in self.active_connections:
            self.active_connections[sid]['last_heartbeat'] = datetime.utcnow()
    
    def record_latency(self, sid: str, latency_ms: float):
        """Record round-trip latency for a client."""
        if sid in self.active_connections:
            latencies = self.active_connections[sid]['latencies']
            latencies.append(latency_ms)
            # Keep only last 100 measurements
            if len(latencies) > 100:
                latencies.pop(0)
    
    def get_client_stats(self, sid: str) -> dict:
        """Get statistics for a specific client."""
        if sid not in self.active_connections:
            return {}
        
        client = self.active_connections[sid]
        latencies = client.get('latencies', [])
        
        return {
            'sid': sid,
            'namespace': client['namespace'],
            'connected_at': client['connected_at'].isoformat(),
            'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'sample_count': len(latencies)
        }
    
    def get_all_stats(self) -> dict:
        """Get aggregate statistics for all clients."""
        total_clients = len(self.active_connections)
        by_namespace = {ns: len(sids) for ns, sids in self.subscriptions.items()}
        
        all_latencies = []
        for client in self.active_connections.values():
            all_latencies.extend(client.get('latencies', []))
        
        return {
            'total_connected_clients': total_clients,
            'clients_by_namespace': by_namespace,
            'avg_latency_ms': sum(all_latencies) / len(all_latencies) if all_latencies else 0,
            'max_latency_ms': max(all_latencies) if all_latencies else 0,
            'p95_latency_ms': sorted(all_latencies)[int(len(all_latencies)*0.95)] if all_latencies else 0
        }


# ==================== Initialize FastAPI + Socket.IO ====================
manager = ConnectionManager()
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=30
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    logger.info("WebSocket server starting...")
    redis_client = await redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    app.state.redis = redis_client
    app.state.manager = manager
    
    # Start heartbeat task
    asyncio.create_task(heartbeat_monitor(sio))
    
    yield
    
    # Shutdown
    logger.info("WebSocket server shutting down...")
    await redis_client.close()


app = FastAPI(title="I2 WebSocket Broadcast Server", lifespan=lifespan)
app.mount('/socket.io', socketio.ASGIApp(sio, static_files={'/': {'filename': 'index.html'}}))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)


# ==================== Socket.IO Event Handlers ====================

@sio.event
async def connect(sid: str, environ):
    """Handle client connection."""
    namespace = environ.get('HTTP_X_NAMESPACE', '/forecast')
    logger.info(f"Client {sid} connecting to {namespace}")
    
    # Validate namespace
    if namespace not in ['/forecast', '/occupancy', '/anomalies']:
        raise ConnectionRefusedError(f"Invalid namespace: {namespace}")
    
    await manager.connect(sid, namespace)
    
    # Send buffered messages to new client
    buffered = await manager.get_buffered_messages(namespace, limit=20)
    if buffered:
        await sio.emit('message_replay', {'messages': buffered}, to=sid)
        logger.info(f"Sent {len(buffered)} buffered messages to {sid}")


@sio.event
async def disconnect(sid: str):
    """Handle client disconnection."""
    await manager.disconnect(sid)


@sio.event
async def ping(sid: str, data: dict):
    """Handle ping from client to measure latency."""
    manager.update_heartbeat(sid)
    
    # Calculate latency
    if 'client_timestamp' in data:
        client_ts = datetime.fromisoformat(data['client_timestamp'])
        latency_ms = (datetime.utcnow() - client_ts).total_seconds() * 1000
        manager.record_latency(sid, latency_ms)
        
        logger.debug(f"Ping from {sid}: {latency_ms:.2f}ms")
    
    # Send pong response
    await sio.emit('pong', {'server_timestamp': datetime.utcnow().isoformat()}, to=sid)


# ==================== REST API Endpoints ====================

@app.get('/health')
async def health_check():
    """Health check endpoint."""
    stats = manager.get_all_stats()
    
    return {
        'status': 'healthy',
        'service': 'i2-websocket-broadcast',
        'timestamp': datetime.utcnow().isoformat(),
        'connections': stats,
        'uptime_seconds': 0  # TODO: Track startup time
    }


@app.get('/metrics')
async def get_metrics():
    """Get connection and latency metrics."""
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'connections': manager.get_all_stats(),
        'buffers': {
            ns: len(manager.message_buffer[ns]) 
            for ns in manager.message_buffer
        }
    }


@app.get('/clients')
async def list_clients():
    """List all connected clients with details."""
    clients = [
        manager.get_client_stats(sid) 
        for sid in manager.active_connections.keys()
    ]
    return {'total': len(clients), 'clients': clients}


@app.post('/broadcast/forecast')
async def broadcast_forecast(forecast: ForecastMessage):
    """Broadcast energy forecast to all connected clients."""
    redis_client = app.state.redis
    
    message = {
        'type': 'forecast',
        'data': forecast.model_dump()
    }
    
    result = await manager.broadcast('/forecast', message, redis_client)
    
    logger.info(f"Forecast broadcast: {result}")
    return {'success': True, 'broadcast_result': result}


@app.post('/broadcast/occupancy')
async def broadcast_occupancy(update: OccupancyUpdate):
    """Broadcast occupancy update to all connected clients."""
    redis_client = app.state.redis
    
    message = {
        'type': 'occupancy_update',
        'data': update.model_dump()
    }
    
    result = await manager.broadcast('/occupancy', message, redis_client)
    
    logger.info(f"Occupancy broadcast: {result}")
    return {'success': True, 'broadcast_result': result}


@app.post('/broadcast/anomaly')
async def broadcast_anomaly(alert: AnomalyAlert):
    """Broadcast anomaly alert to all connected clients (no batching)."""
    redis_client = app.state.redis
    
    message = {
        'type': 'anomaly_alert',
        'data': alert.model_dump()
    }
    
    result = await manager.broadcast('/anomalies', message, redis_client)
    
    logger.warning(f"Anomaly broadcast: {alert.alert_id} - Severity: {alert.severity}")
    return {'success': True, 'broadcast_result': result}


# ==================== Helper Functions ====================

async def heartbeat_monitor(sio_instance):
    """Monitor client heartbeats and detect stale connections."""
    while True:
        try:
            await asyncio.sleep(60)  # Check every minute
            
            now = datetime.utcnow()
            stale_clients = []
            
            for sid, client_info in manager.active_connections.items():
                last_hb = client_info['last_heartbeat']
                if (now - last_hb).total_seconds() > 120:  # 2 minute timeout
                    stale_clients.append(sid)
                    logger.warning(f"Stale client detected: {sid} - no heartbeat for 2+ minutes")
            
            for sid in stale_clients:
                await sio_instance.emit('session_timeout', {}, to=sid)
        
        except Exception as e:
            logger.error(f"Error in heartbeat monitor: {e}")


if __name__ == '__main__':
    import uvicorn
    
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=int(os.getenv('WEBSOCKET_PORT', 8001)),
        log_level='info'
    )
