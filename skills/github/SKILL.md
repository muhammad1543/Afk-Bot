name: github
description: Read, inspect, create and update approved GitHub repository content.
permissions: github_read, github_write

## Workflow
1. Inspect the target repository and existing files.
2. Make the smallest safe change needed.
3. Never overwrite a file blindly; read it first.
4. Report the commit or PR result accurately.

## Safety
Never request or expose access tokens, passwords, cookies or secrets. Do not alter security settings or delete repositories without explicit approval.
