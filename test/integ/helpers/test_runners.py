# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


def run_command(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    output = subprocess.run(args, capture_output=True, check=False)

    print(f"Ran the following: {' '.join(output.args)}")
    print(f"\nstdout:\n\n{output.stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{output.stderr.decode('utf-8', errors='replace')}")

    return output


def run_keyshot_submitter_test(
    keyshot_location: Path, test_script_location: Path, *additional_args
) -> subprocess.CompletedProcess[bytes]:
    args = [
        str(keyshot_location),
    ]

    if additional_args:
        args.extend(["--", *additional_args])

    return run_command(args)


def is_valid_template(template_location: Path) -> bool:
    output = run_command(["openjd", "check", str(template_location), "--output", "json"])
    output_json = json.loads(output.stdout)

    return output_json["status"] == "success"


def run_adaptor_test(template_path: Path, job_params: dict[str, Any]) -> None:
    with open(template_path) as f:
        template = yaml.safe_load(f)

    for step in template["steps"]:
        output = run_command(
            [
                "openjd",
                "run",
                str(template_path),
                "--step",
                step["name"],
                "--job-param",
                json.dumps(job_params),
            ]
        )
        assert output.returncode == 0
