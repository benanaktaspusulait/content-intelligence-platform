-- Profile admission appends its policy version and binding hash to the ruleset identity.
-- Preserve that exact identity and every historical row; VARCHAR(10) rejected real handoffs.
-- PostgreSQL requires dependent views to be recreated even for a widening type change.
DO $$
DECLARE
  stats_definition text;
  failures_definition text;
  stats_comment text;
  failures_comment text;
BEGIN
  SELECT pg_get_viewdef('quality_validation_stats'::regclass, true),
         obj_description('quality_validation_stats'::regclass, 'pg_class')
    INTO stats_definition, stats_comment;
  SELECT pg_get_viewdef('recent_validation_failures'::regclass, true),
         obj_description('recent_validation_failures'::regclass, 'pg_class')
    INTO failures_definition, failures_comment;
  DROP VIEW quality_validation_stats;
  DROP VIEW recent_validation_failures;
  ALTER TABLE quality_validations ALTER COLUMN ruleset_version TYPE varchar(200);
  EXECUTE 'CREATE VIEW quality_validation_stats AS ' || stats_definition;
  EXECUTE 'CREATE VIEW recent_validation_failures AS ' || failures_definition;
  EXECUTE format('COMMENT ON VIEW quality_validation_stats IS %L', stats_comment);
  EXECUTE format('COMMENT ON VIEW recent_validation_failures IS %L', failures_comment);
END $$;
