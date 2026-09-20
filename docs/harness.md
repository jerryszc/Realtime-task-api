# HARNESS: Python & PostgreSQL Development Environment

## 1. Environment & Terminal Constraints
- **OS & Terminal:** Windows 10, Git Bash (mandatory POSIX-style paths using forward slashes `/`). Backslashes `\` are strictly forbidden.
- **Encoding & Syntax:** UTF-8 file encoding. **Strict prohibition of accents or special characters** in code comments or strings to prevent Windows decoding errors.
- **Editors:** Visual Studio Code.

## 2. Code Standards & Version Control
- **Language:** Python 3.10+ with strict Type Hints and PEP 8 standards.
- **Version Control:** Git and GitHub. Clear, descriptive commits for every feature block.

## 3. Mandatory Security & Database Integrity
- **Credentials:** Zero hardcoded secrets. Mandatory use of environment variables via `pydantic-settings` (`.env`).
- **Database & Transactions:** Explicit transaction management (`commit`/`rollback`) inside exception blocks (`try/except/finally`) using SQLModel/SQLAlchemy context managers.
- **Migrations:** All schema modifications must go through Alembic automated migrations (`alembic revision --autogenerate`). Manual DDL SQL execution is forbidden.

## 4. Testing & Quality Assurance
- **Testing:** Mandatory execution of automated tests using `pytest` for business logic, endpoints, and database interactions within isolated sessions.