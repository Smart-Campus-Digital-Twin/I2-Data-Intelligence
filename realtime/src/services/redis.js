/**
 * Redis Pub/Sub service for Socket.IO relay
 * Subscribes to Redis channels and emits Socket.IO events
 */

const Redis = require('ioredis');

class RedisService {
  constructor(redisUrl = 'redis://localhost:6379') {
    // Separate connections for Pub/Sub and key-value reads
    this.subscriber = new Redis(redisUrl, {
      retryStrategy: (times) => Math.min(times * 50, 2000),
      reconnectOnError: (err) => {
        const targetError = 'READONLY';
        if (err.message.includes(targetError)) {
          return true;
        }
        return false;
      },
    });

    this.keyvalueClient = new Redis(redisUrl, {
      retryStrategy: (times) => Math.min(times * 50, 2000),
    });

    this.subscriptions = new Map();
    this.setupErrorHandlers();
  }

  setupErrorHandlers() {
    this.subscriber.on('error', (err) => {
      console.error('Redis Subscriber error:', err);
    });

    this.subscriber.on('connect', () => {
      console.log('Redis Subscriber connected');
    });

    this.subscriber.on('reconnecting', () => {
      console.log('Redis Subscriber reconnecting...');
    });

    this.keyvalueClient.on('error', (err) => {
      console.error('Redis KV Client error:', err);
    });

    this.keyvalueClient.on('connect', () => {
      console.log('Redis KV Client connected');
    });
  }

  /**
   * Subscribe to a Redis channel and handle messages
   * @param {string} channel - Redis channel name
   * @param {function} handler - Message handler function
   */
  subscribe(channel, handler) {
    this.subscriber.subscribe(channel, (err, count) => {
      if (err) {
        console.error(`Failed to subscribe to ${channel}:`, err);
      } else {
        console.log(`Subscribed to ${channel} (total subscriptions: ${count})`);
      }
    });

    this.subscriber.on('message', (ch, message) => {
      if (ch === channel) {
        try {
          handler(message);
        } catch (error) {
          console.error(`Error handling message from ${channel}:`, error);
        }
      }
    });

    this.subscriptions.set(channel, handler);
  }

  /**
   * Subscribe to keyspace notifications (e.g., key expiration)
   * @param {string} pattern - Keyspace pattern (e.g., '__:expired')
   * @param {function} handler - Message handler function
   */
  subscribeKeyspace(pattern, handler) {
    // Pattern format: __keyevent@0__:expired for DB 0 expiration events
    this.subscriber.subscribe(`__keyevent@0__:${pattern}`, (err, count) => {
      if (err) {
        console.error(`Failed to subscribe to keyspace ${pattern}:`, err);
      } else {
        console.log(`Subscribed to keyspace ${pattern} (total subscriptions: ${count})`);
      }
    });

    this.subscriber.on('message', (ch, message) => {
      if (ch.includes(pattern)) {
        try {
          handler(message);
        } catch (error) {
          console.error(`Error handling keyspace message for ${pattern}:`, error);
        }
      }
    });
  }

  /**
   * Get a value from Redis
   * @param {string} key - Redis key
   * @returns {Promise<string|null>} - Value or null if not found
   */
  async get(key) {
    try {
      return await this.keyvalueClient.get(key);
    } catch (error) {
      console.error(`Error getting key ${key}:`, error);
      return null;
    }
  }

  /**
   * Get a value and parse as JSON
   * @param {string} key - Redis key
   * @returns {Promise<object|null>} - Parsed JSON or null
   */
  async getJSON(key) {
    try {
      const value = await this.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error(`Error parsing JSON from key ${key}:`, error);
      return null;
    }
  }

  /**
   * Check if Redis is connected
   * @returns {boolean}
   */
  isConnected() {
    return this.subscriber.status === 'ready' && this.keyvalueClient.status === 'ready';
  }

  /**
   * Graceful shutdown
   */
  async disconnect() {
    console.log('Disconnecting Redis...');
    await this.subscriber.quit();
    await this.keyvalueClient.quit();
    console.log('Redis disconnected');
  }
}

module.exports = RedisService;
