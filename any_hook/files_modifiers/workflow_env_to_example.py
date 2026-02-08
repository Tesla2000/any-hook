from collections.abc import Iterable
from pathlib import Path
from typing import Any
from typing import Literal

import yaml
from any_hook._file_data import FileData
from any_hook.files_modifiers._modifier import Modifier
from pydantic import Field


class WorkflowEnvToExample(Modifier):
    type: Literal["workflow-env-to-example"] = "workflow-env-to-example"
    workflow_paths: tuple[Path, ...] = Field(
        description="Paths to workflow files to extract env variables from"
    )
    output_path: Path = Field(
        default=Path(".env.example"),
        description="Path to the .env.example file to write to",
    )

    def modify(self, data: Iterable[FileData]) -> bool:
        env_vars = self._collect_env_vars_from_workflows()
        if not env_vars:
            self._output("No environment variables found in workflow files")
            return False
        existing_content, existing_vars = self._read_existing_env_file()
        new_sections, added_vars = self._build_new_sections(
            env_vars, existing_vars
        )
        if not new_sections:
            self._output(
                "All environment variables already present in .env.example"
            )
            return False
        self._write_updated_env_file(existing_content, new_sections)
        self._output(
            f"Updated {self.output_path} with {len(added_vars)} new environment variable(s)"
        )
        return True

    def _collect_env_vars_from_workflows(self) -> dict[str, dict[str, str]]:
        env_vars: dict[str, dict[str, str]] = {}
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
                env_vars[source_name] = source_envs
        return env_vars

    def _read_existing_env_file(self) -> tuple[str, set[str]]:
        existing_content = ""
        existing_vars: set[str] = set()
        if self.output_path.exists():
            existing_content = self.output_path.read_text()
            for line in existing_content.splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    var_name = line.split("=")[0].strip()
                    existing_vars.add(var_name)
        return existing_content, existing_vars

    @staticmethod
    def _build_new_sections(
        env_vars: dict[str, dict[str, str]], existing_vars: set[str]
    ) -> tuple[list[str], set[str]]:
        new_sections: list[str] = []
        added_vars: set[str] = set()
        for source, vars_dict in env_vars.items():
            section_vars: list[str] = []
            for var_name, var_value in vars_dict.items():
                if (
                    var_name not in existing_vars
                    and var_name not in added_vars
                ):
                    section_vars.append(f"{var_name}={var_value}")
                    added_vars.add(var_name)
            if section_vars:
                new_sections.append(f"# From: {source}")
                new_sections.extend(section_vars)
                new_sections.append("")
        return new_sections, added_vars

    def _write_updated_env_file(
        self, existing_content: str, new_sections: list[str]
    ) -> None:
        final_content = existing_content.rstrip()
        if final_content:
            final_content += "\n\n"
        final_content += "\n".join(new_sections)
        self.output_path.write_text(final_content)

    def _extract_env_vars(self, data: Any) -> dict[str, str]:
        env_vars: dict[str, str] = {}
        if isinstance(data, dict):
            if "env" in data:
                env_section = data["env"]
                if isinstance(env_section, dict):
                    for key, value in env_section.items():
                        env_vars[key] = str(value) if value is not None else ""
            for value in data.values():
                env_vars.update(self._extract_env_vars(value))
        elif isinstance(data, list):
            for item in data:
                env_vars.update(self._extract_env_vars(item))
        return env_vars
