# SSO / OIDC Design Document

**Status:** Design only (v3.0 scope)

## Overview

This document outlines the SSO integration design for the AI Workflow Control Plane. The platform currently supports local password-based authentication with RBAC. SSO enables enterprise users to authenticate via their existing identity provider (IdP).

## Supported Protocols

### OIDC (OpenID Connect)

Primary protocol for new integrations. Built on OAuth 2.0 with standardized identity layer.

**Flow:** Authorization Code with PKCE

```
User → Browser → /auth/oidc/login
  → Redirect to IdP authorization endpoint
  → User authenticates at IdP
  → IdP redirects back with authorization code
  → Backend exchanges code for tokens
  → Backend validates ID token, creates/updates user
  → Session created, redirect to dashboard
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/oidc/login` | GET | Initiate OIDC flow, generates state + nonce |
| `/auth/oidc/callback` | GET | Handle IdP callback, exchange code |
| `/auth/oidc/logout` | GET | End session, optionally redirect to IdP logout |
| `/auth/oidc/.well-known` | GET | Discovery document for auto-configuration |

**Configuration (per IdP):**

```json
{
  "provider": "oidc",
  "issuer": "https://idp.example.com",
  "client_id": "...",
  "client_secret": "... (encrypted)",
  "scopes": ["openid", "profile", "email"],
  "redirect_uri": "https://control-plane.example.com/auth/oidc/callback",
  "jwks_uri": "https://idp.example.com/.well-known/jwks.json"
}
```

### SAML 2.0

For enterprises with existing SAML infrastructure.

**Flow:** SP-Initiated SSO

```
User → Browser → /auth/saml/login
  → Generate AuthnRequest
  → Redirect to IdP SSO URL
  → User authenticates at IdP
  → IdP POSTs SAML Response to SP ACS URL
  → Backend validates assertion, creates/updates user
  → Session created, redirect to dashboard
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/saml/login` | GET | Initiate SAML flow |
| `/auth/saml/acs` | POST | Assertion Consumer Service |
| `/auth/saml/metadata` | GET | SP metadata XML |
| `/auth/saml/slo` | GET/POST | Single Logout |

## User Provisioning

### Just-In-Time (JIT) Provisioning

Default approach. User record created on first SSO login.

```
On first SSO login:
  1. Extract email, name, groups from ID token / SAML assertion
  2. Check if user exists by email
  3. If not: create User with sso_provider, sso_external_id
  4. If yes: update sso_external_id, last login
  5. Map IdP groups → platform roles (configurable)
```

**Group-to-Role Mapping:**

```json
{
  "mappings": [
    {"idp_group": "platform-admins", "role": "admin"},
    {"idp_group": "developers", "role": "operator"},
    {"idp_group": "viewers", "role": "viewer"}
  ],
  "default_role": "viewer"
}
```

### SCIM (System for Cross-domain Identity Management)

For automated user lifecycle management (future enhancement).

- User creation/deactivation synced from IdP
- Group membership changes propagated
- Endpoint: `/scim/v2/Users`, `/scim/v2/Groups`

## Session Management

### Session Storage

- Server-side sessions stored in database (not JWT-only)
- Session table: `user_sessions(id, user_id, provider, created_at, expires_at, ip_address, user_agent)`
- Configurable TTL (default: 8 hours for SSO, 30 days for local)

### Token Refresh

- Access tokens: short-lived (15 minutes)
- Refresh tokens: stored server-side, rotated on use
- Silent refresh via iframe or background request

### Logout

- Local logout: clear session, redirect to login
- SSO logout: redirect to IdP end_session_endpoint
- SLO (Single Logout): propagate logout to all sessions

## Multi-IdP Support

The platform supports multiple identity providers simultaneously.

**Database Table: `sso_provisions`**

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| provider_type | String(20) | `oidc` or `saml` |
| display_name | String(100) | Human-readable name |
| issuer | String(500) | IdP issuer URL |
| client_id | String(255) | OIDC client ID |
| client_secret | String(500) | Encrypted client secret |
| metadata_url | String(500) | OIDC discovery or SAML metadata URL |
| enabled | Boolean | Active flag |
| team_id | UUID | Optional: restrict to specific team |
| config_json | JSON | Additional provider-specific config |
| created_at | Timestamp | Creation time |

**Login Page:** Shows configured IdPs as buttons. Users select their provider.

## Security Considerations

1. **PKCE** mandatory for OIDC (no implicit flow)
2. **State parameter** validated on callback to prevent CSRF
3. **Nonce** validated in ID token to prevent replay attacks
4. **Token validation**: signature, issuer, audience, expiry, nonce
5. **SAML assertion validation**: signature, conditions, audience restriction
6. **Encrypted client secrets** stored via Fernet (v3.0 secret management)
7. **Rate limiting** on auth endpoints (5 attempts/minute)
8. **Audit logging** for all authentication events

## Implementation Phases

### Phase 1: OIDC Core (v3.1)
- OIDC authorization code flow with PKCE
- JIT user provisioning
- Group-to-role mapping
- Session management

### Phase 2: SAML 2.0 (v3.2)
- SP-initiated SSO
- SAML assertion validation
- Attribute mapping

### Phase 3: SCIM & Enterprise (v3.3)
- SCIM user/group provisioning
- Multi-IdP support
- Team-scoped IdP assignment
- SLO propagation

## Dependencies

- `authlib` — OIDC/SAML client library
- `python-jose` — JWT validation (or `pyjwt`)
- `python3-saml` — SAML 2.0 SP library
- `cryptography` — already included for Fernet (v3.0)

## Configuration

Environment variables:

```
SSO_ENABLED=false
SSO_DEFAULT_PROVIDER=oidc
SSO_SESSION_TTL_HOURS=8
SSO_REFRESH_TTL_DAYS=7
SSO_JIT_PROVISIONING=true
SSO_DEFAULT_ROLE=viewer
```
