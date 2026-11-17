
# Development Guidelines

## Coding Rules

- **Follow the existing style** of the code around your change.
- **Keep it DRY.** Reuse existing code instead of duplicating it.
- **No hacks.** Write high-quality code, not a workaround.
- **Respect module boundaries.** Each component has a clear responsibility. Don't leak logic across boundaries.
- **Prefer incremental implementation.** Land small, working changes rather than large speculative ones. Each change should leave the project in a compilable, testable state.
- **Keep tasks independently testable.** Every unit of work should be verifiable on its own without requiring unrelated components to be finished first.
- **Write unit tests for every object.** Each class, struct, trait implementation, or public module must have corresponding unit tests. Tests are not an afterthought — they are part of the implementation, not a follow-up task.
- **Write comments for an international audience.** Use simple, clear English. No idioms, no slang, no redundancy. One short sentence max. If a well-named identifier already explains the intent, don't add a comment.
- **Line width.** 150–200 characters is fine — don't wrap lines artificially short. In multi-line comments, break at the end of each sentence rather than trying to make all lines the same length.
- **Code Formatting**: Ensure your code adheres to the auto-formatting configuration included in the devcontainer.
- **Linting**: Resolve all linting issues automatically detected in the devcontainer.
- **Backward Compatibility**: Avoid introducing breaking changes to
  - database schemas
  - structure of object storage
  - flatbuffer schema of objects stored in object storage
  - REST API
  - formats of NATS message or KV store values

## Testing

- Run all unit tests to verify the correctness of your changes.
- Execute end-to-end (e2e) tests to ensure the system behaves as expected.

## Definition of Done

A task is complete when all of the following are true:

- Compiles without warnings
- Unit tests exist for each object introduced or modified
- All tests pass
- Public APIs are documented
- A pull request is submitted, merge conflicts are resolved and CI failures are addressed
