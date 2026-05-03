from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

import pytest

from any_hook.files_modifiers.workflow_env_to_example import (
    WorkflowEnvToExample,
)


class TestWorkflowEnvToExample:
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
            assert result
            assert output_file.exists()
            content = output_file.read_text()
            assert f"# From: {workflow_file}" in content
            assert "DATABASE_URL=postgres://localhost/test" in content
            assert "API_KEY=test_key" in content

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
            assert result
            content = output_file.read_text()
            assert "TEST_VAR=test_value" in content

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
            assert result
            content = output_file.read_text()
            assert "STEP_VAR=step_value" in content

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
            assert result
            content = output_file.read_text()
            assert content.count("DATABASE_URL") == 1
            assert "NEW_VAR=new_value" in content

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
            assert result
            content = output_file.read_text()
            assert content.count("DATABASE_URL") == 1
            assert content.count(str(workflow_file)) == 1
            assert "NEW_VAR=new_value" in content

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
            assert result
            content = output_file.read_text()
            assert f"# From: {workflow1}" in content
            assert f"# From: {workflow2}" in content
            assert "VAR1=value1" in content
            assert "VAR2=value2" in content

    def test_raises_on_missing_workflow_file(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "nonexistent.yml"
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            with pytest.raises(FileNotFoundError):
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
            assert not result

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
            assert not result

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
            assert result
            content = output_file.read_text()
            assert "EMPTY_VAR=" in content
            assert "VAR_WITH_VALUE=some_value" in content

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
            assert result
            content = output_file.read_text()
            assert "GH_TOKEN=\n" in content
            assert "API_KEY=\n" in content
            assert "${{" not in content
            assert "secrets" not in content
            assert "REGULAR_VAR=regular_value" in content

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
            assert result
            content = output_file.read_text()
            assert "IGNORE_ME" not in content
            assert "ALSO_IGNORE" not in content
            assert "KEEP_ME=kept_value" in content

    def test_skips_non_dict_yaml_content(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text("---\n- item1\n- item2\n")
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,),
                output_path=output_file,
            )
            result = modifier.modify([])
            assert result is False

    def test_handles_existing_env_file_with_variables_and_comments(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                env:
                  NEW_VAR: new_value
            """))
            output_file = tmpdir_path / ".env.example"
            output_file.write_text(
                "# This is a comment\nEXISTING_VAR=old_value\n"
            )
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            assert result
            content = output_file.read_text()
            assert "EXISTING_VAR=old_value" in content
            assert "NEW_VAR=new_value" in content

    def test_handles_non_dict_env_section(self):
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            workflow_file = tmpdir_path / "workflow.yml"
            workflow_file.write_text(dedent("""
                name: Test
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    env: "string_instead_of_dict"
                    steps:
                      - name: Step
                        env:
                          STEP_VAR: step_value
            """))
            output_file = tmpdir_path / ".env.example"
            modifier = WorkflowEnvToExample(
                workflow_paths=(workflow_file,), output_path=output_file
            )
            result = modifier.modify([])
            assert result
            content = output_file.read_text()
            assert "STEP_VAR=step_value" in content
