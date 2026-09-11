# Instructions & Behavioral Rules

- NEVER do something not explicitly requested. Strictly stick to scope given by the user.
- NEVER open a browser or run checks unless asked. The user handles verification.
- Job is the code and the code only.
- Do NOT make any changes to the environment; the user handles environment changes.
- ALWAYS use internal file reading and writing tools instead of terminal glue commands (no cat << EOF, sed, or echo tricks).
- WSL File Access Protocol:
  - Internal file tools (`write_to_file`, `replace_file_content`) write directly into the agent artifact scratch directory (`C:\Users\hp\.gemini\antigravity-ide\brain\<conversation-id>\scratch\`).
  - In WSL, this scratch directory is immediately accessible via the mount `/mnt/c/Users/hp/.gemini/antigravity-ide/brain/<conversation-id>/scratch/`.
  - Transfer/sync to target project paths cleanly via standard directory copy, avoiding all shell escaping bugs.
- The paths are in WSL; if you need something, ask the user.
- Only check git to inspect a previous version of the code.
- NO TIME or token wasting.
- When finished the work, a one-line verdict of what is done is enough.
