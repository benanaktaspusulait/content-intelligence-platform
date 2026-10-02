# Performance Import

Preview first:

```bash
./pompom import-performance export.xlsx --preview --platform instagram
```

Commit and rebuild derived trajectories:

```bash
./pompom import-performance export.xlsx --platform instagram
./pompom rebuild-trajectories
```

Review unresolved rows with `./pompom unresolved-imports`. Imported source files are never edited. Re-importing identical bytes reports `ALREADY IMPORTED`.

