import json
import os
import shutil
import subprocess
from pathlib import Path


def run_gitleaks(repo_path):
    # Проверка, что Gitleaks установлен
    if not shutil.which("gitleaks"):
        raise EnvironmentError("Gitleaks is not installed or not found in PATH")

    # Создание выходной директории, если не существует
    # Path(repo_path).mkdir(parents=True, exist_ok=True)

    # # Команды для запуска Gitleaks с указанием путей к отчетам
    report_git = os.path.join(repo_path, "report_git.json")
    report_no_git = os.path.join(repo_path, "report_no_git.json")
    command_git = [
        "gitleaks",
        "detect",
        "--source",
        repo_path,
        "--report-format",
        "json",
        "--report-path",
        report_git,
        "--no-banner",
        "--exit-code",
        "2",
    ]
    command_no_git = [
        "gitleaks",
        "detect",
        "--source",
        repo_path,
        "--report-format",
        "json",
        "--report-path",
        report_no_git,
        "--no-banner",
        "--no-git",
        "--exit-code",
        "2",
    ]

    all_findings = []

    for command, report_path in [(command_git, report_git), (command_no_git, report_no_git)]:
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0:
                # No leaks present
                continue
            if result.returncode == 1:
                print("Error")
                continue
            elif result.returncode == 2:
                # Leaks encountered, try to read the report
                try:
                    with open(report_path, "r") as report_file:
                        report = json.load(report_file)
                        all_findings.extend(report)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading or decoding JSON from report file {report_path}: {e}")
            elif result.returncode == 126:
                print(f"Unknown flag encountered in command: {command}")
            else:
                print(f"Unexpected return code {result.returncode} for command: {command}")
        except subprocess.CalledProcessError as e:
            print(f"Error running Gitleaks with command {command}: {e.stderr}")

    # Удаление дубликатов
    unique_findings = {
        f"{finding['File']}{finding['Secret']}{finding['RuleID']}": finding for finding in all_findings
    }

    return list(unique_findings.values())


def parse_gitleaks_report(report):
    for finding in report:
        print(f"File: {finding['file']}")
        print(f"Secret: {finding['secret']}")
        print(f"Rule: {finding['ruleID']}")
        print(f"Line: {finding['line']}")
        print("-" * 20)
