-- V2: Non-destructive copy of legacy render data from the backend-owned `public` schema into the
-- render-owned `creative_render` schema.
--
-- Safety properties:
--   * Guarded by to_regclass(...) so it is a no-op on a fresh deploy where public render tables do
--     not exist.
--   * Only ever SELECTs from public.* -- never ALTER/UPDATE/DELETE/DROP of any source table.
--   * INSERT ... ON CONFLICT (id) DO NOTHING makes the copy idempotent (safe to re-run).
--   * Dependency-ordered: render_jobs -> render_assets -> render_qa_results, openart_credit_log.
--   * Verifies row count and a deterministic id-set hash per table; RAISEs on any mismatch so a
--     partial/incorrect copy aborts the migration.
--   * Immutable prompt snapshots are materialized from public.contents / public.prompt_versions,
--     with prompt_sha256 computed as the hex SHA-256 of the prompt raw text (pgcrypto digest).
--
-- Runs with search_path = creative_render (Flyway default-schema), so unqualified objects resolve
-- in creative_render; public tables are always schema-qualified.

DO $$
DECLARE
    v_src_count BIGINT;
    v_tgt_count BIGINT;
    v_src_hash  TEXT;
    v_tgt_hash  TEXT;
BEGIN
    -- 1) render_jobs (+ immutable prompt snapshot derived from public contents/prompt_versions)
    IF to_regclass('public.render_jobs') IS NOT NULL
       AND to_regclass('public.contents') IS NOT NULL
       AND to_regclass('public.prompt_versions') IS NOT NULL THEN

        INSERT INTO creative_render.render_jobs (
            id, content_id, prompt_version_id,
            content_title_snapshot, prompt_version_number_snapshot, prompt_sha256, prompt_text_snapshot,
            job_type, openart_job_id, openart_model, openart_params,
            status, attempt_number, max_attempts,
            credits_estimated, credits_actual,
            queued_at, started_at, completed_at, failed_at,
            error_code, error_message,
            created_at, updated_at, entity_version
        )
        SELECT
            rj.id, rj.content_id, rj.prompt_version_id,
            c.title,
            pv.version_number,
            encode(digest(pv.raw_text, 'sha256'), 'hex'),
            pv.raw_text,
            rj.job_type, rj.openart_job_id, rj.openart_model, rj.openart_params,
            rj.status, rj.attempt_number, rj.max_attempts,
            rj.credits_estimated, rj.credits_actual,
            rj.queued_at, rj.started_at, rj.completed_at, rj.failed_at,
            rj.error_code, rj.error_message,
            rj.created_at, rj.updated_at, rj.entity_version
        FROM public.render_jobs rj
        JOIN public.prompt_versions pv ON pv.id = rj.prompt_version_id
        JOIN public.contents c ON c.id = rj.content_id
        ON CONFLICT (id) DO NOTHING;

        SELECT count(*) INTO v_src_count FROM public.render_jobs;
        SELECT count(*) INTO v_tgt_count FROM creative_render.render_jobs;
        IF v_tgt_count <> v_src_count THEN
            RAISE EXCEPTION 'legacy copy render_jobs count mismatch: source=%, target=% (missing content/prompt rows for some jobs?)',
                v_src_count, v_tgt_count;
        END IF;

        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_src_hash FROM public.render_jobs;
        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_tgt_hash FROM creative_render.render_jobs;
        IF v_tgt_hash IS DISTINCT FROM v_src_hash THEN
            RAISE EXCEPTION 'legacy copy render_jobs id-set hash mismatch: source=%, target=%',
                v_src_hash, v_tgt_hash;
        END IF;

        INSERT INTO creative_render.legacy_copy_audit
            (source_table, source_count, target_count, source_hash, target_hash, status)
        VALUES ('render_jobs', v_src_count, v_tgt_count, v_src_hash, v_tgt_hash, 'VERIFIED');
    END IF;

    -- 2) render_assets (depends on render_jobs)
    IF to_regclass('public.render_assets') IS NOT NULL THEN
        INSERT INTO creative_render.render_assets (
            id, render_job_id, content_id, asset_type, relative_path, file_size_bytes,
            duration_ms, width, height, frame_rate, codec,
            download_url, downloaded_at, is_current, created_at, entity_version,
            asset_version
        )
        SELECT
            ra.id, ra.render_job_id, ra.content_id, ra.asset_type, ra.relative_path, ra.file_size_bytes,
            ra.duration_ms, ra.width, ra.height, ra.frame_rate, ra.codec,
            ra.download_url, ra.downloaded_at, ra.is_current, ra.created_at, ra.entity_version,
            COALESCE(NULLIF(substring(ra.relative_path FROM 'v([0-9]+)'), '')::INTEGER, 1)
        FROM public.render_assets ra
        ON CONFLICT (id) DO NOTHING;

        SELECT count(*) INTO v_src_count FROM public.render_assets;
        SELECT count(*) INTO v_tgt_count FROM creative_render.render_assets;
        IF v_tgt_count <> v_src_count THEN
            RAISE EXCEPTION 'legacy copy render_assets count mismatch: source=%, target=%',
                v_src_count, v_tgt_count;
        END IF;

        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_src_hash FROM public.render_assets;
        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_tgt_hash FROM creative_render.render_assets;
        IF v_tgt_hash IS DISTINCT FROM v_src_hash THEN
            RAISE EXCEPTION 'legacy copy render_assets id-set hash mismatch';
        END IF;

        INSERT INTO creative_render.legacy_copy_audit
            (source_table, source_count, target_count, source_hash, target_hash, status)
        VALUES ('render_assets', v_src_count, v_tgt_count, v_src_hash, v_tgt_hash, 'VERIFIED');
    END IF;

    -- 3) render_qa_results (depends on render_assets)
    IF to_regclass('public.render_qa_results') IS NOT NULL THEN
        INSERT INTO creative_render.render_qa_results (
            id, render_asset_id, prompt_version_id, decision, decision_reason, confidence,
            compliance_score, compliance_issues,
            has_dead_air, dead_air_segments,
            character_identity_verified, character_identity_issues,
            physics_consistent, physics_violations,
            has_object_duplication, duplication_details,
            final_execution_score, final_execution_issues,
            requires_human_review, human_reviewed_at, human_reviewer, human_decision, human_notes,
            created_at, entity_version
        )
        SELECT
            qa.id, qa.render_asset_id, qa.prompt_version_id, qa.decision, qa.decision_reason, qa.confidence,
            qa.compliance_score, qa.compliance_issues,
            qa.has_dead_air, qa.dead_air_segments,
            qa.character_identity_verified, qa.character_identity_issues,
            qa.physics_consistent, qa.physics_violations,
            qa.has_object_duplication, qa.duplication_details,
            qa.final_execution_score, qa.final_execution_issues,
            qa.requires_human_review, qa.human_reviewed_at, qa.human_reviewer, qa.human_decision, qa.human_notes,
            qa.created_at, qa.entity_version
        FROM public.render_qa_results qa
        ON CONFLICT (id) DO NOTHING;

        SELECT count(*) INTO v_src_count FROM public.render_qa_results;
        SELECT count(*) INTO v_tgt_count FROM creative_render.render_qa_results;
        IF v_tgt_count <> v_src_count THEN
            RAISE EXCEPTION 'legacy copy render_qa_results count mismatch: source=%, target=%',
                v_src_count, v_tgt_count;
        END IF;

        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_src_hash FROM public.render_qa_results;
        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_tgt_hash FROM creative_render.render_qa_results;
        IF v_tgt_hash IS DISTINCT FROM v_src_hash THEN
            RAISE EXCEPTION 'legacy copy render_qa_results id-set hash mismatch';
        END IF;

        INSERT INTO creative_render.legacy_copy_audit
            (source_table, source_count, target_count, source_hash, target_hash, status)
        VALUES ('render_qa_results', v_src_count, v_tgt_count, v_src_hash, v_tgt_hash, 'VERIFIED');
    END IF;

    -- 4) openart_credit_log (depends on render_jobs). The render-side table added columns
    --    (prompt_version_id, job_type, openart_job_id, openart_model, credits_used); legacy rows
    --    only carry credits_spent, so credits_used is backfilled from COALESCE(credits_spent, 0)
    --    and the new descriptive columns are left NULL.
    IF to_regclass('public.openart_credit_log') IS NOT NULL THEN
        INSERT INTO creative_render.openart_credit_log (
            id, render_job_id, prompt_version_id, job_type, openart_job_id, openart_model,
            operation, operation_metadata,
            credits_before, credits_spent, credits_used, credits_after,
            logged_at
        )
        SELECT
            cl.id, cl.render_job_id, NULL::BIGINT, NULL::VARCHAR, NULL::VARCHAR, NULL::VARCHAR,
            cl.operation, cl.operation_metadata,
            cl.credits_before, cl.credits_spent, COALESCE(cl.credits_spent, 0), cl.credits_after,
            cl.logged_at
        FROM public.openart_credit_log cl
        ON CONFLICT (id) DO NOTHING;

        SELECT count(*) INTO v_src_count FROM public.openart_credit_log;
        SELECT count(*) INTO v_tgt_count FROM creative_render.openart_credit_log;
        IF v_tgt_count <> v_src_count THEN
            RAISE EXCEPTION 'legacy copy openart_credit_log count mismatch: source=%, target=%',
                v_src_count, v_tgt_count;
        END IF;

        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_src_hash FROM public.openart_credit_log;
        SELECT md5(string_agg(id::text, ',' ORDER BY id)) INTO v_tgt_hash FROM creative_render.openart_credit_log;
        IF v_tgt_hash IS DISTINCT FROM v_src_hash THEN
            RAISE EXCEPTION 'legacy copy openart_credit_log id-set hash mismatch';
        END IF;

        INSERT INTO creative_render.legacy_copy_audit
            (source_table, source_count, target_count, source_hash, target_hash, status)
        VALUES ('openart_credit_log', v_src_count, v_tgt_count, v_src_hash, v_tgt_hash, 'VERIFIED');
    END IF;
END $$;
