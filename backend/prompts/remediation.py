"""Prompt for AI-powered incident remediation with smart action routing."""


def build_remediation_prompt(description: str, diagnosis: str, past_incidents: str) -> str:
    return f"""You are an expert Site Reliability Engineer preparing a remediation plan for a production incident.

INCIDENT REPORT:
{description}

DIAGNOSIS:
{diagnosis}

SIMILAR PAST INCIDENTS AND RESOLUTIONS:
{past_incidents}

REPOSITORY CONTEXT:
The project is hosted at GitHub. Key files in the repo:
- login_app/app.py - Flask login application with authentication routes
- login_app/templates/login.html - Login page template
- login_app/templates/dashboard.html - Dashboard page template
- login_app/requirements.txt - Python dependencies

The login_app/app.py uses SQLite with a table called 'users' (columns: id, username, password, email).
The app runs on EC2 as a systemd service called 'login-app'.

IMPORTANT: You must decide the correct ACTION TYPE for this incident. Choose ONE:

- "code_fix" — when the root cause is a bug in the code (wrong query, typo, logic error). Requires a PR.
- "restart_instance" — when the EC2 instance is unresponsive or needs a full reboot.
- "restart_service" — when the application service crashed but the server is fine.
- "cleanup_disk" — when disk space is full or near capacity.
- "scale_up" — when CPU/memory is high due to traffic, need more instances.
- "config_change" — when a configuration value needs updating (timeouts, connection strings, etc.).
- "run_command" — when a specific shell command needs to run on the server.

Based on the diagnosis, provide a remediation plan with the appropriate action.

Return as valid JSON:
{{
  "action_type": "code_fix OR restart_instance OR restart_service OR cleanup_disk OR scale_up OR config_change OR run_command",
  "suggested_fix": "Clear description of what should be done to fix this",
  "immediate_actions": ["step 1", "step 2", "step 3"],
  "root_cause_fix": "Long-term fix to prevent recurrence",
  "severity": "low or medium or high or critical",
  "estimated_resolution_time": "e.g., 2 minutes, 15 minutes, 1 hour",
  "customer_message": "Brief message to send back to the reporter",

  "action_params": {{
    "instance_id": "i-xxxxx (if applicable, extract from the alarm/description)",
    "service_name": "login-app (if restart_service)",
    "asg_name": "asg-name (if scale_up)",
    "commands": ["shell commands to run (if run_command)"],
    "config_file": "/path/to/config (if config_change)",
    "find": "old config value (if config_change)",
    "replace": "new config value (if config_change)"
  }},

  "code_fix": {{
    "file_path": "login_app/app.py (only if action_type is code_fix)",
    "find": "the exact buggy code to find",
    "replace": "the corrected code to replace with"
  }},

  "files_to_change": ["affected file paths"],
  "code_suggestion": "Brief code snippet or command showing the fix",
  "pr_description": "What the pull request should describe (only if code_fix)"
}}

RULES:
- If the alarm mentions CPU/memory and no code bug: use "scale_up" or "restart_service"
- If the alarm mentions disk/filesystem: use "cleanup_disk"
- If the server/instance is down: use "restart_instance"
- If there's a code error (OperationalError, TypeError, 500 with traceback): use "code_fix"
- If a service crashed but server is up: use "restart_service"
- If a config value is wrong (timeout, connection string): use "config_change"
- For action_params, include the instance_id if found in the description (format: i-xxxxx)
"""
