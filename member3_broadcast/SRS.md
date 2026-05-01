# Software Requirements Specification

## 1. Introduction

### 1.1 Purpose

This SRS defines the requirements for Member 3, the real-time WebSocket and data broadcast service for the Smart Campus Digital Twin project. The service delivers low-latency updates for energy forecasts, occupancy changes, and anomaly alerts to connected frontend clients.

### 1.2 Scope

The system is an async event distribution layer that consumes data from upstream services and streams it to clients through Socket.IO namespaces. It is designed to support:

- energy forecast broadcasts from Member 1
- occupancy state and anomaly alerts from Member 2
- real-time client subscriptions from the frontend
- audit logging and latency tracking

### 1.3 Definitions

- **Socket.IO**: WebSocket-friendly real-time transport with fallback support.
- **Namespace**: Logical channel used to separate forecast, occupancy, and anomaly traffic.
- **SLA**: Service level agreement for response or broadcast latency.
- **JWT**: JSON Web Token used to authenticate clients.

## 2. Product Overview

### 2.1 Product Perspective

The service sits between the backend intelligence services and the frontend application. It does not own domain data; it receives, buffers, formats, and forwards live events.

### 2.2 Product Functions

- Authenticate client connections with JWT.
- Register and manage connected clients.
- Broadcast forecast events to the `/forecast` namespace.
- Broadcast occupancy delta updates to the `/occupancy` namespace.
- Broadcast anomaly alerts to the `/anomalies` namespace.
- Record latency and client count metrics.
- Expose a health endpoint for dependency checks.

### 2.3 User Classes

- **Frontend user**: subscribes to live campus data.
- **System operator**: monitors health, latency, and availability.
- **Backend integrator**: connects the service to Kafka, Redis, PostgreSQL, and upstream APIs.

### 2.4 Operating Environment

- Python 3.11+
- FastAPI
- Socket.IO ASGI server
- Optional Redis, Kafka, and PostgreSQL connections
- Containerized deployment recommended

## 3. Functional Requirements

### FR-1 Connection Authentication

The system shall validate client connections using JWT from query parameters.

### FR-2 Namespace Separation

The system shall provide three namespaces: `/forecast`, `/occupancy`, and `/anomalies`.

### FR-3 Forecast Broadcast

The system shall broadcast energy forecast payloads to all connected clients in the forecast namespace.

### FR-4 Occupancy Broadcast

The system shall broadcast occupancy updates, including room, building, classification, and confidence.

### FR-5 Anomaly Broadcast

The system shall broadcast anomaly alerts immediately to subscribed clients.

### FR-6 Client Tracking

The system shall track connected clients and their active subscriptions.

### FR-7 Health Check

The system shall expose a health endpoint returning service and dependency status.

### FR-8 Audit Logging

The system shall record event type, namespace, data size, latency, and timestamp for each broadcast.

## 4. Non-Functional Requirements

### NFR-1 Latency

Broadcast operations should complete in sub-second time under normal load.

### NFR-2 Scalability

The service should support horizontal scaling behind a load balancer.

### NFR-3 Reliability

Transient upstream failures should not stop broadcasts from previously cached data.

### NFR-4 Security

Client connections must be authenticated, and invalid tokens must be rejected.

### NFR-5 Maintainability

The codebase should keep transport, schema, and service logic separated.

### NFR-6 Observability

The system should expose logs, metrics, and audit records for debugging and SLA validation.

## 5. External Interface Requirements

### 5.1 API Interfaces

- HTTP health endpoint: `GET /health`
- Socket.IO connection endpoint: `/socket.io`
- Namespaces: `/forecast`, `/occupancy`, `/anomalies`

### 5.2 Data Interfaces

The service consumes:

- forecast payloads from Member 1
- occupancy state and alerts from Member 2
- optional Kafka topics for stream-based integration

The service emits:

- real-time payloads to clients
- audit records to PostgreSQL
- optional cache records to Redis

## 6. Data Requirements

### 6.1 Forecast Payload

- building identifier
- timestamp array
- predicted kW values
- confidence bounds
- summary statistics

### 6.2 Occupancy Payload

- building identifier
- room identifier
- occupancy count
- classification
- confidence score
- timestamp

### 6.3 Anomaly Payload

- anomaly identifier
- building and room references
- severity
- expected and actual counts
- divergence metrics
- timestamp

### 6.4 Audit Payload

- event type
- namespace
- client count
- payload size
- latency
- timestamp

## 7. Use Cases

### UC-1 Subscribe to forecasts

A frontend client connects to the forecast namespace and receives the latest energy prediction broadcast.

### UC-2 Receive occupancy deltas

A client on the occupancy namespace receives only meaningful changes to room occupancy.

### UC-3 Receive anomaly alerts

A client on the anomalies namespace receives alerts immediately when a high-confidence anomaly occurs.

### UC-4 Operator checks health

An operator calls the health endpoint to confirm the service and upstream dependencies are available.

## 8. Constraints

- The service must use async I/O end to end.
- Broadcast logic should avoid blocking operations.
- Connection auth must happen before subscription acceptance.
- The design must support future Kafka and Redis integration without major refactoring.

## 9. Acceptance Criteria

- Valid JWT clients can connect successfully.
- Invalid JWT clients are rejected.
- All three namespaces are available.
- Health endpoint returns a valid JSON response.
- Broadcast payload schemas are documented and testable.

## 10. Evolution Plan

The first release should cover connection auth, health checks, payload schemas, and mocked broadcasters. The next change request should add live Kafka consumers, Redis replay buffers, and PostgreSQL audit persistence with load testing evidence.

## 11. Detailed Interface Behavior

### 11.1 Connection Flow

1. Client connects to one of the Socket.IO namespaces.
2. The server extracts the JWT token from the query string.
3. The token is validated before subscription is accepted.
4. On success, the client session is tracked in memory.
5. On disconnect, the session is removed from active tracking.

### 11.2 Broadcast Flow

1. The service receives or generates a new forecast, occupancy, or anomaly payload.
2. The payload is serialized to JSON.
3. The payload is added to the recent-message buffer for that namespace.
4. The payload is broadcast to connected clients.
5. The service records a latency and audit entry.

### 11.3 Failure Handling

- Invalid tokens return a connection rejection.
- Unknown namespace replay requests return 404.
- Upstream service failures should not break existing cached broadcasts.

## 12. Deployment View

The service is intended to run in a container with:

- port 8000 exposed for HTTP and Socket.IO traffic
- environment variables for JWT, Redis, Kafka, and database connectivity
- async workers for low-latency event handling

## 13. Verification Strategy

### 13.1 Unit Testing

- JWT validation
- payload schemas
- broadcast buffer behavior
- metrics generation

### 13.2 Integration Testing

- connection acceptance and rejection
- replay buffer retrieval
- health and metrics endpoints

### 13.3 Load and Resilience Testing

- multiple concurrent Socket.IO clients
- reconnect scenarios
- high-frequency forecast and occupancy updates

## 14. Scope Statement for Presentation

Member 3 is responsible for the real-time distribution layer. It does not perform the machine learning itself and it does not own the campus routing logic. Instead, it receives finished outputs from other members and broadcasts them to the frontend with authentication, buffering, and observability.
