/**
 * JWT authentication service for Socket.IO
 * Validates RS256 tokens from Keycloak using JWKS
 * Supports JWKS key rotation with caching
 */

const jwt = require('jsonwebtoken');
const https = require('https');
const http = require('http');
const NodeCache = require('node-cache');

class JWTService {
  constructor(keycloakUrl, keycloakRealm, keycloakClientId) {
    if (!keycloakUrl || !keycloakRealm || !keycloakClientId) {
      throw new Error(
        'KEYCLOAK_URL, KEYCLOAK_REALM, and KEYCLOAK_CLIENT_ID environment variables are required'
      );
    }
    this.keycloakUrl = keycloakUrl.replace(/\/$/, ''); // Remove trailing slash
    this.keycloakRealm = keycloakRealm;
    this.keycloakClientId = keycloakClientId;
    this.jwksUrl = `${this.keycloakUrl}/realms/${keycloakRealm}/protocol/openid-connect/certs`;
    this.issuer = `${this.keycloakUrl}/realms/${keycloakRealm}`;
    this.audience = keycloakClientId;

    // Cache JWKS keys for 1 hour (3600 seconds)
    this.jwksCache = new NodeCache({ stdTTL: 3600, checkperiod: 600 });
    this.keyCache = new Map();
  }

  /**
   * Fetch JWKS from Keycloak
   * @returns {Promise<object>} - JWKS object with keys array
   */
  async fetchJWKS() {
    const cachedJwks = this.jwksCache.get('jwks');
    if (cachedJwks) {
      return cachedJwks;
    }

    return new Promise((resolve, reject) => {
      // Support both HTTP and HTTPS
      const protocol = this.jwksUrl.startsWith('https') ? https : http;
      const timeout = 5000; // 5 second timeout

      const request = protocol.get(this.jwksUrl, (res) => {
        // Validate response status
        if (res.statusCode !== 200) {
          reject(new Error(`JWKS fetch failed with status ${res.statusCode}`));
          res.resume(); // Consume response data to free up memory
          return;
        }

        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          try {
            const jwks = JSON.parse(data);
            // Clear old keys and cache new ones
            this.keyCache.clear();
            this.jwksCache.set('jwks', jwks);
            jwks.keys.forEach((key) => {
              this.keyCache.set(key.kid, key);
            });
            resolve(jwks);
          } catch (error) {
            reject(new Error(`Failed to parse JWKS: ${error.message}`));
          }
        });
      });

      request.setTimeout(timeout, () => {
        request.destroy();
        reject(new Error(`JWKS fetch timeout after ${timeout}ms`));
      });

      request.on('error', (error) => {
        reject(new Error(`Failed to fetch JWKS: ${error.message}`));
      });
    });
  }

  /**
   * Get signing key from JWKS
   * @param {string} kid - Key ID from JWT header
   * @returns {Promise<string>} - PEM-formatted public key
   */
  async getSigningKey(kid) {
    const cachedKey = this.keyCache.get(kid);
    if (cachedKey) {
      return this.convertJwkToPem(cachedKey);
    }

    const jwks = await this.fetchJWKS();
    const key = jwks.keys.find((k) => k.kid === kid);
    if (!key) {
      throw new Error(`Key with kid "${kid}" not found in JWKS`);
    }
    return this.convertJwkToPem(key);
  }

  /**
   * Convert JWK to PEM format
   * @param {object} jwk - JWK object
   * @returns {string} - PEM-formatted key
   */
  convertJwkToPem(jwk) {
    const NodeRSA = require('node-rsa');
    const key = new NodeRSA(jwk, 'jwk');
    return key.exportKey('pkcs8-pem');
  }

  /**
   * Verify and decode JWT token
   * @param {string} token - JWT token from auth header
   * @returns {Promise<object|null>} - Decoded token payload or null if invalid
   */
  async verify(token) {
    try {
      if (!token) return null;

      // Remove "Bearer " prefix if present
      const cleanToken = token.startsWith('Bearer ') ? token.slice(7) : token;

      // Decode without verification to get kid
      const decoded = jwt.decode(cleanToken, { complete: true });
      if (!decoded || !decoded.header.kid) {
        throw new Error('Invalid token: missing kid in header');
      }

      // Get signing key from JWKS
      const publicKey = await this.getSigningKey(decoded.header.kid);

      // Verify token with RS256 and validate claims
      const verified = jwt.verify(cleanToken, publicKey, {
        algorithms: ['RS256'],
        issuer: this.issuer,
        audience: this.audience,
      });

      return verified;
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
    // Keycloak stores roles in realm_access.roles
    const realmRoles = payload.realm_access?.roles || [];
    const clientRoles = payload.resource_access?.[this.keycloakClientId]?.roles || [];
    return realmRoles.includes('admin') || clientRoles.includes('admin');
  }

  /**
   * Extract user info from token
   * @param {string} token - JWT token
   * @returns {Promise<object|null>} - User info {userId, username, email, role, roles} or null
   */
  async getUserInfo(token) {
    const payload = await this.verify(token);
    if (!payload) return null;

    const realmRoles = payload.realm_access?.roles || [];
    const clientRoles = payload.resource_access?.[this.keycloakClientId]?.roles || [];
    const allRoles = [...new Set([...realmRoles, ...clientRoles])];

    return {
      userId: payload.sub,
      username: payload.preferred_username || payload.username || 'unknown',
      email: payload.email,
      role: this.isAdmin(payload) ? 'admin' : 'user',
      roles: allRoles,
      scope: payload.scope,
    };
  }
}

module.exports = JWTService;
