from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import TestCase

from any_hook.files_modifiers.workflow_env_to_example import (
    WorkflowEnvToExample,
)


class TestWorkflowEnvToExample(TestCase):
    def test_extracts_env_from_workflow_top_level(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  DATABASE_URL: postgres://localhost/test
                  API_KEY: test_key
                jobs:
                  test:
                    runs-on: ubuntu-latest
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            self.assertTrue(output_file.exists())
            content = output_file.read_text()
            self.assertIn(f"# From: {workflow_file}", content)
            self.assertIn("DATABASE_URL=postgres://localhost/test", content)
            self.assertIn("API_KEY=test_key", content)

    def test_extracts_env_from_job_level(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    env:
                      TEST_VAR: test_value
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertIn("TEST_VAR=test_value", content)

    def test_extracts_env_from_step_level(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - name: Run tests
                        env:
                          STEP_VAR: step_value
                        run: echo test
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertIn("STEP_VAR=step_value", content)

    def test_does_not_duplicate_existing_vars(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  DATABASE_URL: postgres://localhost/test
                  NEW_VAR: new_value
            """))
            output_file = tmpdir_path / ".env.example"
            output_file.write_text("DATABASE_URL=existing_value\n")
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertEqual(content.count("DATABASE_URL"), 1)
            self.assertIn("NEW_VAR=new_value", content)

    def test_section_append(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  DATABASE_URL: postgres://localhost/test
                  NEW_VAR: new_value
            """))
            output_file = tmpdir_path / ".env.example"
            output_file.write_text(
                f"# From: {workflow_file}\nDATABASE_URL=existing_value\n"
            )
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertEqual(content.count("DATABASE_URL"), 1)
            self.assertEqual(content.count(str(workflow_file)), 1)
            self.assertIn("NEW_VAR=new_value", content)

    def test_handles_multiple_workflow_files(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow1 = tmpdir_path / "workflow1.yml"
            workflow1.write_text(dedent("""
                name: Test1
                env:
                  VAR1: value1
            """))
            workflow2 = tmpdir_path / "workflow2.yml"
            workflow2.write_text(dedent("""
                name: Test2
                env:
                  VAR2: value2
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow1, workflow2), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertIn(f"# From: {workflow1}", content)
            self.assertIn(f"# From: {workflow2}", content)
            self.assertIn("VAR1=value1", content)
            self.assertIn("VAR2=value2", content)

    def test_raises_on_missing_workflow_file(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "nonexistent.yml"
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            with self.assertRaises(FileNotFoundError):
                modifier.modify([])

    def test_returns_false_when_no_env_vars_found(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                jobs:
                  test:
                    runs-on: ubuntu-latest
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertFalse(result)

    def test_returns_false_when_all_vars_already_present(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  DATABASE_URL: postgres://localhost/test
            """))
            output_file = tmpdir_path / ".env.example"
            output_file.write_text("DATABASE_URL=existing_value\n")
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertFalse(result)

    def test_handles_none_values(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  EMPTY_VAR:
                  VAR_WITH_VALUE: some_value
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertIn("EMPTY_VAR=", content)
            self.assertIn("VAR_WITH_VALUE=some_value", content)

    def test_handles_github_secrets(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  GH_TOKEN: ${{ secrets.GH_TOKEN }}
                  API_KEY: ${{ secrets.API_KEY }}
                  REGULAR_VAR: regular_value
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertIn("GH_TOKEN=\n", content)
            self.assertIn("API_KEY=\n", content)
            self.assertNotIn("${{", content)
            self.assertNotIn("secrets", content)
            self.assertIn("REGULAR_VAR=regular_value", content)

    def test_ignores_specified_names(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  IGNORE_ME: ignored_value
                  KEEP_ME: kept_value
                  ALSO_IGNORE: another_ignored
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,),
                output_path=output_file,
                ignored_names=("IGNORE_ME", "ALSO_IGNORE"),
            )
            result = modifier.modify([])
            self.assertTrue(result)
            content = output_file.read_text()
            self.assertNotIn("IGNORE_ME", content)
            self.assertNotIn("ALSO_IGNORE", content)
            self.assertIn("KEEP_ME=kept_value", content)
