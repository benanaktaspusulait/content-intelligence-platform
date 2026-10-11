# Isolated acceptance database

Any browser or persistent integration acceptance run must set two PostgreSQL URLs and invoke
`assert-isolated-test-database.sh` before opening the UI or sending a mutating request:

```sh
export POMPOM_TEST_DATABASE_URL='postgresql://.../pompom_acceptance_<run-id>'
export POMPOM_APPLICATION_DATABASE_URL='postgresql://.../pompom'
./intelligence/scripts/assert-isolated-test-database.sh
```

The guard resolves both live targets with PostgreSQL (`current_database`, server address and
server port) and refuses to continue when they are the same. It does not trust database names
alone and performs no cleanup. Backend persistence tests already use Testcontainers with
`@DynamicPropertySource`; the guard is for browser/manual acceptance runners, which previously
used the ordinary Docker application and caused the synthetic Idea records in the local DB.

Create the disposable database/container before invoking the guard and destroy that disposable
environment after the run. Never point `POMPOM_TEST_DATABASE_URL` at the ordinary application DB.
