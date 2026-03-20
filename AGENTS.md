# AGENTS.md - Guidelines for Agentic Coding Agents

This file provides guidelines for AI coding agents operating in this repository. It covers build/test/lint commands, code style conventions, and best practices.

## Build, Lint, and Test Commands

### General Commands
- **Installation**: `npm install` or `pip install -r requirements.txt`
- **Development Server**: `npm run dev` or `python -m app.main`
- **Production Build**: `npm run build` or `python -m py_compile src/`
- **Linting**: `npm run lint` or `flake8 src/`
- **Type Checking**: `npm run typecheck` or `mypy src/`
- **Testing**: `npm test` or `pytest tests/`

### Running Specific Tests
- **Single Test File**: `npm test -- src/components/__tests__/Button.test.js` or `pytest tests/test_weather_models.py`
- **Single Test Function**: `npm test -- -t "testButtonClick"` or `pytest tests/test_weather_models.py::test_precipitation_calculation`
- **Watch Mode**: `npm run test:watch` or `pytest -w`
- **Coverage Report**: `npm run test:coverage` or `pytest --cov=src --cov-report=html`

### Common npm/yarn Scripts (if applicable)
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .js,.jsx,.ts,.tsx",
    "lint:fix": "eslint src --ext .js,.jsx,.ts,.tsx --fix",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "format": "prettier --write src/"
  }
}
```

### Common Python Commands (if applicable)
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for dev dependencies

# Run application
python main.py
uvicorn main:app --reload  # for FastAPI

# Linting
flake8 src/
pylint src/
black --check src/
isort --check-only src/

# Formatting
black src/
isort src/

# Testing
pytest tests/
pytest tests/ -v  # verbose
pytest tests/ --cov=src  # with coverage
pytest tests/ -k "test_specific_function"  # run tests matching expression
```

## Code Style Guidelines

### Import Organization
**JavaScript/TypeScript:**
1. Built-in modules (fs, path, etc.)
2. External libraries (react, lodash, etc.)
3. Internal modules (relative paths)
   - Parent directory imports first (`../../utils`)
   - Same directory imports last (`./components`)

**Python:**
1. Standard library imports (os, sys, etc.)
2. Third-party imports (numpy, pandas, etc.)
3. Local application imports (from myapp import ...)

### Formatting
**JavaScript/TypeScript:**
- Use 2 spaces for indentation
- Semicolons required
- Trailing commas in multi-line objects/arrays
- Prefer const over let, never use var
- Arrow functions for callbacks
- Template literals for string concatenation

**Python:**
- Follow PEP 8 (4 spaces for indentation)
- Line length limit: 88 characters (Black default)
- Use descriptive names, avoid single letters except in small scopes
- Docstrings for all public functions/classes using triple double quotes
- Type hints for function signatures and variables

### Type Safety
**TypeScript:**
- Strict mode enabled in tsconfig.json
- Interface over type for object shapes when possible
- Avoid `any` type; use `unknown` when type is uncertain
- Generic constraints for reusable components
- Enum for finite sets of related constants

**Python:**
- Use type hints for all function parameters and return values
- Utilize TypedDict for dictionary schemas
- Prefer dataclasses for data containers
- Protocol for structural typing
- Avoid circular imports with TYPE_CHECKING

### Naming Conventions
**JavaScript/TypeScript:**
- camelCase for variables and functions
- PascalCase for components, classes, and types
- UPPER_SNAKE_CASE for constants
- Descriptive names; avoid abbreviations unless universally understood
- Boolean variables: isEnabled, hasLoaded, shouldValidate

**Python:**
- snake_case for variables and functions
- PascalCase for classes and exceptions
- UPPER_SNAKE_CASE for constants
- Descriptive names; avoid single letters except in small loops
- Boolean variables: is_valid, has_data, needs_processing

### Error Handling
**JavaScript/TypeScript:**
- Prefer async/await over .then() chains
- Always handle promise rejections with try/catch
- Custom Error classes for domain-specific errors
- Validate inputs at function boundaries
- Never ignore errors with empty catch blocks

**Python:**
- Use try/except blocks for specific exceptions
- Avoid bare except: clauses
- Raise specific exceptions with descriptive messages
- Custom exception classes inheriting from Exception
- Validate inputs early (fail fast principle)
- Use context managers (with statement) for resource handling

### Comments and Documentation
- Explain why, not what (unless the what is complex)
- Keep comments updated with code changes
- JSDoc for JavaScript/TypeScript functions
- Docstrings for Python functions/classes
- README.md for project overview
- Inline comments for non-obvious logic
- Avoid commented-out code; use version control instead

### Git Workflow
- Commit early, commit often
- Descriptive commit messages in present tense
- Feature branches for new work
- Pull requests for code review
- Rebase feature branches onto main before merging
- Delete merged branches

### Testing Principles
- Write tests alongside implementation (TDD when possible)
- Test behavior, not implementation details
- Mock external dependencies (APIs, databases)
- Test edge cases and error conditions
- Keep tests fast and reliable
- Test coverage is valuable but not the goal; meaningful tests are

### Performance Considerations
- Lazy load non-critical resources
- Memoize expensive computations
- Use efficient data structures and algorithms
- Avoid unnecessary re-renders/recursions
- Profile before optimizing
- Consider bundle size for frontend applications

### Security Guidelines
- Validate and sanitize all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Keep dependencies updated
- Store secrets in environment variables, never in code
- Use HTTPS in production
- Implement rate limiting for APIs