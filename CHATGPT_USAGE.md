# ChatGPT Usage Transparency

This document outlines how ChatGPT and other AI tools were used in the development of this project.

## General Usage

ChatGPT was used as a coding assistant throughout the development process to:
- Generate boilerplate code and project structure
- Debug issues and find solutions
- Understand best practices for Django Channels and WebSocket implementation


## Specific Prompts and Usage

### 1. Project Structure Setup
**Prompt**: "Help me set up a Django project with Channels for WebSocket support, including proper ASGI configuration"

**Usage**: Used to understand the correct way to configure Django Channels and ASGI application for WebSocket support.

### 2. Analytics Engine
**Prompt**: "Implement statistical functions for z-score, OLS regression, ADF test, and rolling correlation using numpy, pandas, and statsmodels"

**Usage**: Generated the core analytics functions in `analytics/engine.py`. The functions were tested and refined to match our data structures.

### 4. Frontend Dashboard
**Prompt**: "Create an HTML/CSS/JavaScript dashboard with Plotly charts that connects to WebSocket and displays real-time data"

**Usage**: Generated the initial structure for the dashboard HTML and JavaScript. The styling was customized to match a modern dark theme, and functionality was extended for our specific use case.

### 6. Documentation
**Prompt**: "Generate a comprehensive README.md for a Binance analytics platform with installation, usage, and API documentation"

**Usage**: Created the structure and content for README.md, which was then customized with project-specific details.

## Code Quality

All code generated with AI assistance was:
- Reviewed for correctness
- Tested for functionality
- Modified to fit project requirements
- Documented with comments
- Structured following Django best practices
