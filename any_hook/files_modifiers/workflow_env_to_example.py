from collections.abc import Iterable
from pathlib import Path
from typing import Any
from typing import Literal

import yaml
from any_hook._file_data import FileData
from any_hook.files_modifiers._modifier import Modifier
from pydantic import BaseModel
from pydantic import Field


class _EnvFileState(BaseModel):
    env_vars: dict[str, dict[str, str]] = Field(default_factory=dict)
    existing_content: str = ""
    existing_vars: set[str] = Field(default_factory=set)
    source_sections: dict[str, int] = Field(default_factory=dict)
    existing_source_vars: dict[str, list[str]] = Field(default_factory=dict)
    new_source_sections: dict[str, list[str]] = Field(default_factory=dict)
    added_vars: set[str] = Field(default_factory=set)


class WorkflowEnvToExample(Modifier):
    type: Literal["workflow-env-to-example"] = "workflow-env-to-example"
    workflow_paths: tuple[Path, ...] = Field(
        description="Paths to workflow files to extract env variables from"
    )
    output_path: Path = Field(
        default=Path(".env.example"),
        description="Path to the .env.example file to write to",
    )
    source_comment_prefix: str = Field(
        default="# From: ",
        description="Prefix used for source comments in the output file",
    )

    def modify(self, _: Iterable[FileData]) -> bool:
        state = _EnvFileState()
        self._collect_env_vars_from_workflows(state)
        if not state.env_vars:
            return False
        self._read_existing_env_file(state)
        self._build_new_sections(state)
        if not state.existing_source_vars and not state.new_source_sections:
            return False
        self._write_updated_env_file(state)
        self._output(
            f"Updated {self.output_path} with {len(state.added_vars)} new environment variable(s)"
        )
        return True

    def _collect_env_vars_from_workflows(self, state: _EnvFileState) -> None:
        for workflow_path in self.workflow_paths:
            if not workflow_path.exists():
                raise FileNotFoundError(
                    f"Workflow file {workflow_path} does not exist"
                )
            source_name = str(workflow_path)
            workflow_data = yaml.safe_load(workflow_path.read_text())
            if not isinstance(workflow_data, dict):
                continue
            source_envs = self._extract_env_vars(workflow_data)
            if source_envs:
                state.env_vars[source_name] = source_envs

    def _read_existing_env_file(self, state: _EnvFileState) -> None:
        if not self.output_path.exists():
            return
        state.existing_content = self.output_path.read_text()
        lines = state.existing_content.splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(self.source_comment_prefix):
                source = stripped.removeprefix(self.source_comment_prefix)
                state.source_sections[source] = idx
            elif "=" in line and not stripped.startswith("#"):
                var_name = line.split("=")[0].strip()
                state.existing_vars.add(var_name)

    def _build_new_sections(self, state: _EnvFileState) -> None:
        for source, vars_dict in state.env_vars.items():
            section_vars: list[str] = []
            for var_name, var_value in vars_dict.items():
                if (
                    var_name not in state.existing_vars
                    and var_name not in state.added_vars
                ):
                    section_vars.append(f"{var_name}={var_value}")
                    state.added_vars.add(var_name)
            if section_vars:
                if source in state.source_sections:
                    state.existing_source_vars[source] = section_vars
                else:
                    state.new_source_sections[source] = section_vars

    def _write_updated_env_file(self, state: _EnvFileState) -> None:
        content = state.existing_content
        if state.existing_source_vars:
            lines = content.splitlines()
            for source, vars_to_add in state.existing_source_vars.items():
                section_idx = state.source_sections[source]
                insert_idx = section_idx + 1
                while (
                    insert_idx < len(lines)
                    and lines[insert_idx].strip()
                    and not lines[insert_idx].strip().startswith("#")
                ):
                    insert_idx += 1
                for var_line in reversed(vars_to_add):
                    lines.insert(insert_idx, var_line)
            content = "\n".join(lines)
        final_content = content.rstrip()
        if state.new_source_sections:
            if final_content:
                final_content += "\n\n"
            new_sections_lines: list[str] = []
            for source, vars_list in state.new_source_sections.items():
                new_sections_lines.append(
                    f"{self.source_comment_prefix}{source}"
                )
                new_sections_lines.extend(vars_list)
                new_sections_lines.append("")
            final_content += "\n".join(new_sections_lines)
        self.output_path.write_text(final_content)

    def _extract_env_vars(self, data: Any) -> dict[str, str]:
        env_vars: dict[str, str] = {}
        if isinstance(data, dict):
            if "env" in data:
                env_section = data["env"]
                if isinstance(env_section, dict):
                    for key, value in env_section.items():
                        if value is None:
                            env_vars[key] = ""
                        else:
                            str_value = str(value)
                            env_vars[key] = (
                                "" if "${{" in str_value else str_value
                            )
            for value in data.values():
                env_vars.update(self._extract_env_vars(value))
        elif isinstance(data, list):
            for item in data:
                env_vars.update(self._extract_env_vars(item))
        return env_vars
