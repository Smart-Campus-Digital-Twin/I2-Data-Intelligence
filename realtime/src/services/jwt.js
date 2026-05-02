/**
 * JWT authentication service for Socket.IO
 * Validates HS256 tokens and extracts user info
 */

const jwt = require('jsonwebtoken');

class JWTService {
  constructor(secret) {
    if (!secret) {
      throw new Error('JWT_SECRET environment variable is required');
    }
    this.secret = secret;
  }

  /**
   * Verify and decode JWT token
   * @param {string} token - JWT token from auth header
   * @returns {object|null} - Decoded token payload or null if invalid
   */
  verify(token) {
    try {
      if (!token) return null;

      // Remove "Bearer " prefix if present
      const cleanToken = token.startsWith('Bearer ') ? token.slice(7) : token;

      const decoded = jwt.verify(cleanToken, this.secret, {
        algorithms: ['HS256'],
      });

      return decoded;
    } catch (error) {
      console.error('JWT verification failed:', error.message);
      return null;
    }
  }

  /**
   * Check if user has admin role
   * @param {object} payload - Decoded JWT payload
   * @returns {boolean} - True if user is admin
   */
  isAdmin(payload) {
    if (!payload) return false;
    return payload.role === 'admin' || payload.roles?.includes('admin');
  }

  /**
   * Extract user info from token
   * @param {string} token - JWT token
   * @returns {object|null} - User info {userId, username, role} or null
   */
  getUserInfo(token) {
    const payload = this.verify(token);
    if (!payload) return null;

    return {
      userId: payload.sub || payload.userId || payload.id,
      username: payload.username || payload.user || 'unknown',
      role: payload.role || 'user',
      scope: payload.scope,
    };
  }
}

module.exports = JWTService;
