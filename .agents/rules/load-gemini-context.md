# Load Project Context (GEMINI.md)

On boot or at the start of every session, you MUST load and follow the context provided in `.gemini/GEMINI.md`.

## Instructions
1.  **Read Context:** Immediately read the contents of `file:///.gemini/GEMINI.md` (root-relative) to understand the current project goals, architecture, and technology stack.
2.  **Prioritization:** The context in `GEMINI.md` takes precedence over any generic assumptions about the project, but is subordinate to the logic-specific rules defined in other `.agents/rules/*.md` files.
3.  **Consistency:** Ensure all code generations and architectural decisions align with the "Primary Goal" and "Architectural Patterns" sections of `GEMINI.md`.
