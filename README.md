# SRA Web Application V9 — Security & User Management

Python + Flask + PostgreSQL. V9 adds authenticated sessions, role-based access, password hashing, CSRF protection for POST forms, safer redirects, and an admin user-management screen while preserving V8/V7 resource-allocation functionality.

## Run
1. Configure PostgreSQL as used by `main.py`.
2. Optional environment variables: `SRA_SECRET_KEY`, `SRA_ADMIN_USERNAME`, `SRA_ADMIN_PASSWORD`.
3. Run `run_web.bat`.
4. Open `http://127.0.0.1:5000`.

If no admin password is supplied, the demo account is `admin` / `admin123`. Change this before any deployment.

## Roles
- **Admin:** full management and allocation-changing operations.
- **User:** authenticated read-only access to dashboards, recommendations, analytics, and optimization/advisory views.
