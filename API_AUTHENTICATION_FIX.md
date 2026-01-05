# 403 Forbidden Error - API Authentication Fix

## Problem
The `/api/users/me/` endpoint was returning **403 Forbidden** errors even after successful login.

```
Forbidden: /api/users/me/
[05/Jan/2026 09:19:54] "GET /api/users/me/ HTTP/1.1" 403 58
```

## Root Cause
The issue had two parts:

### 1. Missing REST Framework Authentication Configuration
The `REST_FRAMEWORK` settings in `settings.py` didn't specify:
- **Authentication classes** - How to authenticate requests (missing SessionAuthentication)
- **CORS credentials** - Permission to send/receive cookies across origins
- **Default permissions** - What authentication is required by default

Without these, Django REST Framework couldn't properly authenticate session-based requests from the React frontend.

### 2. Frontend Not Sending Session Cookies
The axios API client wasn't configured to:
- Send cookies with requests (`withCredentials: true`)
- Receive cookies from responses

This meant the session cookie created during login wasn't being attached to subsequent API requests.

## Solution

### Backend Fix: `/app/config/settings.py`
Added proper REST Framework configuration:

```python
# Enable CORS credentials (cookies)
CORS_ALLOW_CREDENTIALS = True

# Configure REST Framework authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}
```

**What this does:**
- `SessionAuthentication`: Uses Django's session mechanism (via cookies) for authentication
- `CORS_ALLOW_CREDENTIALS`: Tells browser to allow sending credentials (cookies) with cross-origin requests
- `IsAuthenticated`: Default permission requiring authentication for all endpoints (except those with `AllowAny`)

### Frontend Fix: `/facetrack-frontend/src/api/client.js`
Configured axios to send cookies with requests:

```javascript
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,  // ← ADD THIS
});
```

**What this does:**
- `withCredentials: true`: Tells axios to send cookies with all requests (including cross-origin)
- Enables receiving and storing cookies from responses

## How It Works Now

1. **Login Flow**:
   - Frontend POSTs to `/api/users/login/` with credentials
   - Django authenticates user and calls `login(request, user)`
   - Django sets `sessionid` cookie in response
   - Axios (with `withCredentials: true`) stores the cookie

2. **Authenticated Requests**:
   - Frontend GETs `/api/users/me/`
   - Axios automatically includes `sessionid` cookie
   - Django REST Framework's `SessionAuthentication` reads the cookie
   - User is authenticated ✅
   - Returns 200 with user profile data

3. **Logout Flow**:
   - Frontend POSTs to `/api/users/logout/`
   - Django calls `logout(request)` which invalidates the session
   - `sessionid` cookie is cleared

## Files Modified

1. **[app/config/settings.py](app/config/settings.py)**
   - Added `CORS_ALLOW_CREDENTIALS = True`
   - Added `DEFAULT_AUTHENTICATION_CLASSES` with `SessionAuthentication`
   - Added `DEFAULT_PERMISSION_CLASSES` with `IsAuthenticated`

2. **[facetrack-frontend/src/api/client.js](facetrack-frontend/src/api/client.js)**
   - Added `withCredentials: true` to axios config

## Verification

After these changes:
- ✅ Login endpoint returns user data and sets session cookie
- ✅ GET `/api/users/me/` returns 200 with authenticated user profile
- ✅ Logout clears session and subsequent `/api/users/me/` returns 401
- ✅ Protected routes (ProtectedRoute component) can verify authentication

## Key Concepts

**Session Authentication**: Uses server-side sessions with cookies
- Cookie is set when user logs in
- Cookie is automatically sent by browser/axios with every request
- Server validates cookie and authenticates user

**CORS with Credentials**: Allows cookies to be sent across origins
- By default, browsers don't send cookies with cross-origin requests (security)
- Both server (`CORS_ALLOW_CREDENTIALS`) and client (`withCredentials`) must allow it

**REST Framework Permissions**: Control who can access endpoints
- `AllowAny`: No authentication required (signup, login)
- `IsAuthenticated`: User must be authenticated (me, logout, protected routes)

## Testing

Test the fix with:
```bash
# 1. Signup/Login
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  -c cookies.txt

# 2. Get profile (should work with cookies)
curl -X GET http://localhost:8000/api/users/me/ \
  -b cookies.txt

# 3. Frontend should work automatically now
```

Or simply:
1. Navigate to http://localhost:5173 (React frontend)
2. Sign up for new account
3. Should see authenticated navbar with username and profile link
4. /profile page should load successfully
