#!/usr/bin/env python3
"""Safety tests for the embedded Python in reset-creative-studio.sh; no database writes."""
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('reset-creative-studio.sh')
source = SCRIPT.read_text().split("<<'PYTHON'\n", 1)[1].rsplit('\nPYTHON', 1)[0]
reset = types.ModuleType('creative_studio_reset')
with patch.object(sys, 'argv', ['-', str(SCRIPT.parents[2])]):
    exec(compile(source, str(SCRIPT), 'exec'), reset.__dict__)


class ResetSafetyTest(unittest.TestCase):
    def scope(self):
        return {name: [] for name in reset.TARGETS}

    def reference_check(self, data, scope, fks=None, fk_count=0):
        def query(sql):
            return fk_count if sql.startswith('SELECT count(*)') else (fks or [])
        with patch.object(reset, 'rows', side_effect=lambda table: data.get(table, [])), patch.object(reset, 'query', side_effect=query):
            return reset.protected_references(list(data), scope)

    def test_numeric_id_is_not_a_prompt_version_number(self):
        scope = self.scope()
        scope['public.prompt_versions'] = [8]
        self.assertEqual(reset.predicate('public.prompt_versions', [8]), '"id" IN (\'8\')')
        self.assertFalse(self.reference_check({'public.metrics': [{'id': 8, 'version_number': 8}]}, scope))

    def test_rejects_numeric_sql_injection(self):
        with self.assertRaises(RuntimeError):
            reset.predicate('public.contents', ['1); DELETE FROM videos; --'])

    def test_rejects_unknown_table(self):
        with self.assertRaises(RuntimeError):
            reset.predicate('public.videos', [1])

    def test_empty_allowlist_never_generates_blanket_delete(self):
        self.assertEqual(reset.predicate('public.contents', []), 'FALSE')

    def test_unknown_uuid_is_not_interpreted_as_numeric_identity(self):
        with self.assertRaises(ValueError):
            reset.predicate('public.post_family_workflow_events', ['1'])

    def test_protected_video_blocks_prompt_deletion(self):
        scope = self.scope()
        scope['public.prompt_versions'] = [8]
        hits = self.reference_check({'public.video_prompt_links': [{'id': 1, 'prompt_version_id': 8}]}, scope)
        self.assertEqual(hits[0]['identity_path'], '.prompt_version_id')

    def test_protected_learning_event_blocks_story_deletion(self):
        story = '556ed974-b163-408b-bfaa-ebe0243bf3e5'
        scope = self.scope()
        scope['public.post_family_workflow_events'] = [story]
        hits = self.reference_check({'public.post_family_workflow_events': [
            {'id': story, 'kind': 'CREATIVE_ROLE', 'payload': {}},
            {'id': 'protected', 'kind': 'LEARNING_REVIEW', 'payload': {'sourceStoryRecordId': story}},
        ]}, scope)
        self.assertEqual(hits[0]['row_id'], 'protected')

    def test_target_event_linked_to_preserved_content_blocks_cleanup(self):
        story = '556ed974-b163-408b-bfaa-ebe0243bf3e5'
        scope = self.scope()
        scope['public.post_family_workflow_events'] = [story]
        hits = self.reference_check({
            'public.contents': [{'id': 99, 'status': 'PUBLISHED'}],
            'public.post_family_workflow_events': [{'id': story, 'payload': {'contentId': 99}}],
        }, scope)
        self.assertEqual(hits[0]['reason'], 'Target belongs to preserved operational data')

    def test_cross_schema_foreign_key_blocks_cleanup(self):
        scope = self.scope()
        scope['public.quality_validations'] = [7]
        hits = self.reference_check({}, scope, [{
            'child': 'creative_render.render_jobs', 'parent': 'public.quality_validations',
            'conname': 'job_validation', 'child_columns': ['validation_record_id'], 'parent_columns': ['id'],
        }], fk_count=1)
        self.assertEqual(hits[0]['protected_child'], 'creative_render.render_jobs')

    def test_real_qa_and_learning_kinds_are_not_reset_candidates(self):
        self.assertTrue({'LEARNING_REVIEW', 'ACTUAL_RENDER_QA', 'ASSOCIATION', 'EDIT_HANDOFF', 'REGENERATION_HANDOFF'}.isdisjoint(reset.TEST_EVENT_KINDS))

    def test_provenance_exception_restores_only_named_trigger_inside_transaction(self):
        scope = self.scope()
        scope['public.prompt_creative_provenance'] = [8]
        before = {table: {'count': len(ids), 'rows_md5': 'a' * 32} for table, ids in scope.items()}
        after = {table: {'count': 0, 'rows_md5': 'b' * 32} for table in scope}
        sql = reset.cleanup_sql({'allowlists': scope, 'before': before, 'expected_after': after, 'schema_md5': 'c' * 32})
        self.assertLess(sql.index('BEGIN;'), sql.index('DISABLE TRIGGER'))
        self.assertLess(sql.index('ENABLE TRIGGER'), sql.index('COMMIT;'))
        self.assertIn("WHERE \"prompt_version_id\" IN ('8')", sql)
        self.assertNotIn('DISABLE TRIGGER ALL', sql)
        self.assertNotIn('TRUNCATE', sql)
        self.assertNotIn('CASCADE', sql)
        self.assertNotIn('RESTART IDENTITY', sql)

    def test_manifest_digest_changes_when_ids_change(self):
        a = {'allowlists': {'public.contents': [1]}, 'before': {'count': 1}}
        b = {'allowlists': {'public.contents': [2]}, 'before': {'count': 1}}
        self.assertNotEqual(reset.digest(a), reset.digest(b))

    def test_global_row_drift_guards_are_generated_before_deletion(self):
        scope = self.scope()
        scope['public.contents'] = [1]
        before = {table: {'count': len(ids), 'rows_md5': 'a' * 32} for table, ids in scope.items()}
        before['public.videos'] = {'count': 50, 'rows_md5': 'c' * 32}
        after = {table: dict(data) for table, data in before.items()}
        after['public.contents'] = {'count': 0, 'rows_md5': 'b' * 32}
        sql = reset.cleanup_sql({'allowlists': scope, 'before': before, 'expected_after': after, 'schema_md5': 'd' * 32})
        self.assertLess(sql.index('Inventory mismatch: public.videos'), sql.index('DELETE FROM public.contents'))
        self.assertEqual(sql.count('Inventory mismatch: public.videos'), 2)


if __name__ == '__main__':
    unittest.main()
