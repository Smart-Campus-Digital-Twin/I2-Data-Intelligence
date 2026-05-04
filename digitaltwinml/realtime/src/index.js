/**
 * Socket.IO Real-Time Relay Server for Smart Campus Digital Twin
 * Relays room updates, alerts, and node heartbeats from Redis to connected clients
 *
 * Namespaces:
 * - /twin (authenticated clients): room updates, building subscriptions
 * - /admin (admin-only): node offline events, metrics
 *
 * Ports: 4000
 */

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const promClient = require('prom-client');
const dotenv = require('dotenv');

const JWTService = require('./services/jwt');
const RedisService = require('./services/redis');

dotenv.config();

// ============================================================================
// CONFIGURATION
// ============================================================================

const PORT = process.env.PORT || 4000;
const JWT_SECRET = process.env.JWT_SECRET;
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const ALLOWED_ORIGINS = (process.env.ALLOWED_ORIGINS || 'http://localhost:3000').split(',');

if (!JWT_SECRET) {
  throw new Error('JWT_SECRET environment variable is required');
}

// ============================================================================
// PROMETHEUS METRICS
// ============================================================================

const connectedClientsGauge = new promClient.Gauge({
  name: 'socket_io_connected_clients_total',
  help: 'Total number of connected Socket.IO clients',
});

const roomUpdatesCounter = new promClient.Counter({
  name: 'socket_io_room_updates_emitted_total',
  help: 'Total number of room update events emitted',
});

const alertsCounter = new promClient.Counter({
  name: 'socket_io_alerts_emitted_total',
  help: 'Total number of alert events emitted',
});

const nodeOfflineCounter = new promClient.Counter({
  name: 'socket_io_node_offline_events_total',
  help: 'Total number of node offline events',
});

// ============================================================================
// SETUP
// ============================================================================

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: ALLOWED_ORIGINS,
    methods: ['GET', 'POST'],
    credentials: true,
  },
  transports: ['websocket', 'polling'],
});

const jwtService = new JWTService(JWT_SECRET);
const redisService = new RedisService(REDIS_URL);

// Track connected clients by namespace
const connectedClients = {
  twin: new Map(),
  admin: new Map(),
};

// ============================================================================
// MIDDLEWARE & AUTHENTICATION
// ============================================================================

/**
 * JWT auth middleware for Socket.IO
 */
const authMiddleware = (socket, next) => {
  try {
    const token = socket.handshake.auth.token;
    if (!token) {
      return next(new Error('AUTH_FAILED: No token provided'));
    }

    const userInfo = jwtService.getUserInfo(token);
    if (!userInfo) {
      return next(new Error('AUTH_FAILED: Invalid token'));
    }

    socket.userInfo = userInfo;
    socket.userId = userInfo.userId;
    socket.username = userInfo.username;
    socket.isAdmin = jwtService.isAdmin({ role: userInfo.role });

    next();
  } catch (error) {
    next(new Error('AUTH_FAILED: ' + error.message));
  }
};

/**
 * Admin-only middleware
 */
const adminOnlyMiddleware = (socket, next) => {
  if (!socket.isAdmin) {
    return next(new Error('ADMIN_REQUIRED'));
  }
  next();
};

// ============================================================================
// /TWIN NAMESPACE (Authenticated clients)
// ============================================================================

const twinNs = io.of('/twin');
twinNs.use(authMiddleware);

twinNs.on('connection', (socket) => {
  const clientId = `${socket.userId}:${socket.id}`;
  connectedClients.twin.set(clientId, socket);
  connectedClientsGauge.set(
    connectedClients.twin.size + connectedClients.admin.size
  );

  console.log(`[/twin] Client connected: ${clientId} (${socket.username})`);

  // ---- ROOM SUBSCRIPTION ----
  socket.on('subscribe.room', async (data) => {
    const { roomId } = data;
    if (!roomId) return;

    const roomKey = `room:${roomId}`;
    socket.join(roomKey);

    // Send current state immediately
    const roomState = await redisService.getJSON(`${roomKey}:state`);
    if (roomState) {
      socket.emit('room.update', roomState);
    }

    console.log(`[/twin] ${clientId} subscribed to room ${roomId}`);
  });

  socket.on('unsubscribe.room', (data) => {
    const { roomId } = data;
    if (!roomId) return;

    const roomKey = `room:${roomId}`;
    socket.leave(roomKey);
    console.log(`[/twin] ${clientId} unsubscribed from room ${roomId}`);
  });

  // ---- BUILDING SUBSCRIPTION ----
  socket.on('subscribe.building', async (data) => {
    const { buildingId } = data;
    if (!buildingId) return;

    // Get all rooms in building from Redis
    const roomIds = await redisService.get(`building:${buildingId}:rooms`);
    if (roomIds) {
      const rooms = JSON.parse(roomIds);
      rooms.forEach((roomId) => {
        socket.join(`room:${roomId}`);
      });
      console.log(
        `[/twin] ${clientId} subscribed to building ${buildingId} (${rooms.length} rooms)`
      );
    }
  });

  socket.on('disconnect', () => {
    connectedClients.twin.delete(clientId);
    connectedClientsGauge.set(
      connectedClients.twin.size + connectedClients.admin.size
    );
    console.log(`[/twin] Client disconnected: ${clientId}`);
  });

  socket.on('error', (error) => {
    console.error(`[/twin] Socket error (${clientId}):`, error);
  });
});

// ============================================================================
// /ADMIN NAMESPACE (Admin-only clients)
// ============================================================================

const adminNs = io.of('/admin');
adminNs.use(authMiddleware);
adminNs.use(adminOnlyMiddleware);

adminNs.on('connection', (socket) => {
  const clientId = `${socket.userId}:${socket.id}`;
  connectedClients.admin.set(clientId, socket);
  connectedClientsGauge.set(
    connectedClients.twin.size + connectedClients.admin.size
  );

  console.log(`[/admin] Admin connected: ${clientId} (${socket.username})`);

  socket.on('disconnect', () => {
    connectedClients.admin.delete(clientId);
    connectedClientsGauge.set(
      connectedClients.twin.size + connectedClients.admin.size
    );
    console.log(`[/admin] Admin disconnected: ${clientId}`);
  });

  socket.on('error', (error) => {
    console.error(`[/admin] Socket error (${clientId}):`, error);
  });
});

// ============================================================================
// REDIS PUB/SUB LISTENERS
// ============================================================================

/**
 * Listen for room updates from Spark processor
 * Channel: room-updates
 * Message format: "{roomId}"
 */
redisService.subscribe('room-updates', async (message) => {
  try {
    const roomId = message.trim();
    const roomState = await redisService.getJSON(`room:${roomId}:state`);

    if (roomState) {
      const roomKey = `room:${roomId}`;
      twinNs.to(roomKey).emit('room.update', roomState);
      roomUpdatesCounter.inc();
    }
  } catch (error) {
    console.error('Error processing room update:', error);
  }
});

/**
 * Listen for alert events
 * Channel: alert-events
 * Message format: "{alertId}"
 */
redisService.subscribe('alert-events', async (message) => {
  try {
    const alertId = message.trim();
    const alertData = await redisService.getJSON(`alert:${alertId}`);

    if (alertData) {
      // Emit to all /twin clients
      twinNs.emit('alert.new', alertData);
      alertsCounter.inc();
    }
  } catch (error) {
    console.error('Error processing alert event:', error);
  }
});

/**
 * Listen for node heartbeat expiration (keyspace notifications)
 * Requires: CONFIG SET notify-keyspace-events Ex (in Redis)
 * Event: node:{nodeId}:heartbeat expired
 */
redisService.subscribeKeyspace('expired', (expiredKey) => {
  if (expiredKey.startsWith('node:') && expiredKey.endsWith(':heartbeat')) {
    const nodeId = expiredKey.split(':')[1];
    const now = new Date().toISOString();

    const nodeOfflineEvent = {
      nodeId,
      lastSeen: now,
      reason: 'heartbeat_timeout',
    };

    // Emit to admin clients
    adminNs.emit('node.offline', nodeOfflineEvent);
    nodeOfflineCounter.inc();

    console.log(`[Alert] Node offline: ${nodeId}`);
  }
});

// ============================================================================
// EXPRESS ENDPOINTS
// ============================================================================

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  const redisHealthy = redisService.isConnected();
  const status = redisHealthy ? 'ok' : 'degraded';

  res.status(redisHealthy ? 200 : 503).json({
    status,
    timestamp: new Date().toISOString(),
    redis: {
      connected: redisHealthy,
    },
    socketio: {
      connectedClients: connectedClients.twin.size + connectedClients.admin.size,
      twinNamespace: connectedClients.twin.size,
      adminNamespace: connectedClients.admin.size,
    },
  });
});

/**
 * Prometheus metrics endpoint
 */
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});

/**
 * Server info endpoint
 */
app.get('/info', (req, res) => {
  res.json({
    service: 'Socket.IO Real-Time Relay',
    version: '1.0.0',
    namespaces: {
      twin: {
        description: 'Authenticated clients',
        clients: connectedClients.twin.size,
      },
      admin: {
        description: 'Admin-only clients',
        clients: connectedClients.admin.size,
      },
    },
    redis: {
      connected: redisService.isConnected(),
      subscriptions: Array.from(redisService.subscriptions.keys()),
    },
  });
});

// ============================================================================
// STARTUP & SHUTDOWN
// ============================================================================

process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

async function gracefulShutdown() {
  console.log('Received shutdown signal. Closing gracefully...');

  // Disconnect all clients
  io.disconnectSockets();

  // Close Redis
  await redisService.disconnect();

  // Close server
  server.close(() => {
    console.log('Socket.IO server closed');
    process.exit(0);
  });

  // Force exit after 10 seconds
  setTimeout(() => {
    console.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
}

// ============================================================================
// START SERVER
// ============================================================================

server.listen(PORT, () => {
  console.log(`Socket.IO server listening on port ${PORT}`);
  console.log(`CORS origins: ${ALLOWED_ORIGINS.join(', ')}`);
  console.log('Namespaces: /twin (authenticated), /admin (admin-only)');
});
