# Testing

Run the dependency-free suite:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q pompom_lab
```

The suite covers classification gates, absence of semantic overclaiming, fix-plan validation,
repeatable database migrations, Rescue performance overrides, semantic restraint, and
non-destructive cold-open rendering. The end-to-end smoke gate analyses one real in-scope
Unicode-path video and verifies JSON, Markdown, storyboard, SQLite, and dashboard APIs.
