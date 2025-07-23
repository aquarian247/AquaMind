# AquaMind Authentication Architecture Strategy  
_Last updated: 2025-07-22_

## 0 · Executive Summary
AquaMind will run in **three canonical environments**:

| Environment | Location | Primary Auth | Fallback / Secondary |
|-------------|----------|--------------|----------------------|
| **Local Dev** | Developer laptops / Codespaces | Django username + password (JWT) | — |
| **Shared DEV & TEST** | Public Internet (QA, demos) | Django username + password (JWT) | — |
| **PROD** | Protected VLAN / DMZ | **Active Directory (AD) / LDAP** | Django local accounts (JWT) when AD is unavailable |

This strategy describes how to configure **multi-backend authentication in Django**, expose it via **JWT** for the React frontend, and keep a **non-AD fallback** for business-continuity.

---

## 1 · Multi-Environment Authentication Needs

| Requirement | Rationale | Design Choice |
|-------------|-----------|---------------|
| Internet-exposed dev/test must NOT depend on corporate AD | AD is reachable only from intranet; testers are external | Keep current JWT flow using Django’s default `ModelBackend` |
| Production must use corporate Single Sign-On | Security, account lifecycle, password policies | Integrate **django-auth-ldap** with Active Directory |
| Fallback when AD is down | Avoid total outage during AD maintenance | Chain Django backends: `LDAPBackend` first, `ModelBackend` second |
| Separate “break-glass” admin users | On-call ops can still log in | Maintain a small set of local superusers |
| Clear audit trail of auth source | Compliance & incident forensics | Tag JWT claims with `auth_source` = `ldap` / `local` |

---

## 2 · Django Multi-Backend Setup

### 2.1 Install Dependencies
```bash
pip install django-auth-ldap==4.7
pip install python-ldap==3.4           # system LDAP libs required
pip install djangorestframework-simplejwt
```

### 2.2 `settings.py` Snippet
```python
AUTHENTICATION_BACKENDS = [
    "django_auth_ldap.backend.LDAPBackend",   # AD first
    "django.contrib.auth.backends.ModelBackend",  # Local fallback
]

# --- LDAP / Active Directory ---
import ldap
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

AUTH_LDAP_SERVER_URI = "ldaps://ad.corp.example.com"
AUTH_LDAP_BIND_DN = "CN=svc_aquamind,OU=Service Accounts,DC=corp,DC=example,DC=com"
AUTH_LDAP_BIND_PASSWORD = os.getenv("AD_BIND_PASSWORD")

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "OU=Users,DC=corp,DC=example,DC=com",
    ldap.SCOPE_SUBTREE,
    "(sAMAccountName=%(user)s)"
)

AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0,
    ldap.OPT_NETWORK_TIMEOUT: 5,
}

# Map AD groups → Django groups
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "OU=Groups,DC=corp,DC=example,DC=com",
    ldap.SCOPE_SUBTREE,
    "(objectClass=group)"
)
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
AUTH_LDAP_MIRROR_GROUPS = True

# Populate Django user fields
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}
AUTH_LDAP_ALWAYS_UPDATE_USER = True  # keep names in sync
```

### 2.3 SimpleJWT Settings
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.users.api.serializers.CustomTokenObtainPairSerializer",
}
```

### 2.4 Custom JWT Serializer (adds `auth_source`)
```python
# apps/users/api/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["auth_source"] = "ldap" if user.ldap_user else "local"
        token["full_name"] = user.get_full_name()
        return token
```

### 2.5 Health Check
Add a management command or /health/ endpoint to validate LDAP bind status; surface in Grafana.

---

## 3 · Frontend Implementation Considerations

| Concern | Approach |
|---------|----------|
| **Login UI** | Show single form; backend decides which auth backend to use. Optional dropdown “Log in with Corporate SSO” vs “Local account” if UX requires clarity. |
| **Auth API** | Continue calling `/api/auth/jwt/` (returns JWT regardless of backend). |
| **Token Storage** | Already stored in `localStorage.auth_token`. |
| **Auth Source Display** | Read `auth_source` claim; show badge “AD” vs “Local” in user menu for debugging. |
| **Fallback UX** | If LDAP outage occurs, AD users can still use existing local fallback accounts; optionally display maintenance banner if `auth_source === "local_fallback"`. |

---

## 4 · Fallback Strategy When AD is Down

1. **Backend order** already tries LDAP first, then local.
2. **Monitoring hook**: If LDAP bind errors exceed threshold, send PagerDuty alert.
3. **Pre-created break-glass users**:  
   • `ops_admin` – superuser, long random password stored in vault  
   • MFA enforced on vault access
4. **Periodic password rotation** for break-glass accounts.
5. **Documentation**: Runbook “How to switch AquaMind to LOCAL-ONLY mode” (set `AUTH_BACKENDS=['django.contrib.auth.backends.ModelBackend']` and reload).

---

## 5 · Security & User Provisioning

| Topic | Guideline |
|-------|-----------|
| **Least-Privilege** | Map AD groups → Django groups → DRF role permissions. |
| **Auto-Provisioning** | `django-auth-ldap` creates Django `User` objects on first login; no manual HR/IT workflow needed. |
| **Password Storage** | AD users **do not** store passwords in Django DB. Local accounts use Argon2 hasher. |
| **Audit Trail** | Use DRF request logging + JWT claims for who/when/how. |
| **Token Revocation** | If AD user is disabled, next token refresh fails. Local users follow normal deactivation workflow. |
| **MFA** | Rely on corporate SSO’s MFA; for local accounts enable TOTP via `django-otp` (future). |
| **Data Migration to test env** | Use anonymised fixture loader; local accounts remain, AD auth disabled in dev/test. |

---

## 6 · Implementation Phases

| Phase | Scope | Success Criteria |
|-------|-------|------------------|
| **P0 (Complete)** | Local JWT auth (ModelBackend) | Dev/test login works |
| **P1** | Add ldap settings (disabled by env flag) | `manage.py check --deploy` passes |
| **P2** | Enable LDAP in staging; auto-provision users | AD user can log in, `auth_source='ldap'` |
| **P3** | Map AD groups to Django roles; smoke test permissions | Admin, Manager, Viewer roles enforced |
| **P4** | PROD cut-over; break-glass local accounts documented | AD outage drill: local admin login successful |
| **P5** | MFA & audit hardening | Audit logs show `auth_source`; TOTP for local accounts |

_Environment flags_:  
```env
USE_LDAP_AUTH=true              # staging / prod  
LDAP_SERVER_URI=...             # secrets manager  
AD_BIND_PASSWORD=...            # secrets manager  
```

---

## 7 · Risk Register

| Risk | Mitigation |
|------|------------|
| AD latency slows login | Cache group lookups; keep tokens 12 h |
| Corporate AD schema changes | Version-pin `django-auth-ldap`; monitor bind errors |
| Forgot break-glass password | Rotate & store in 1Password/Hashicorp Vault |
| Mixed-mode confusion | Display `auth_source` clearly in UI; docs for support staff |

---

## 8 · References

* django-auth-ldap docs: <https://django-auth-ldap.readthedocs.io>  
* SimpleJWT docs: <https://django-rest-framework-simplejwt.readthedocs.io>  
* MS AD TLS hardening: KB5005413  
* AquaMind DevOps Runbook: _internal wiki_

---

_Compiled by Janus Lærsson • AquaMind Engineering_  
