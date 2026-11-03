"""
Consolidates the Semgrep output into the report the agent evaluation consumes.
Runs inside the CodeBuild SAST stage. Exits non-zero when the scan did not really
happen, which stops the pipeline before an empty report can read as "no findings".
"""
import datetime
import json
import os
import sys
import tempfile


def resolve_in_work_dir(path):
    """Resolve a path, rejecting anything outside the build's temporary directory."""
    work_dir = os.path.realpath(tempfile.gettempdir())
    resolved = os.path.realpath(path)
    if not resolved.startswith(work_dir + os.sep):
        raise ValueError(f'Path outside {work_dir}: {path}')
    return resolved


def consolidate(semgrep_output):
    """Build the consolidated report, raising ValueError if the scan is unusable."""
    if 'results' not in semgrep_output:
        raise ValueError('Semgrep output has no results section')

    scanned = semgrep_output.get('paths', {}).get('scanned', [])
    if not scanned:
        raise ValueError('Semgrep scanned no files: the .zip is empty or has no supported code')

    return {
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scan_type': 'SAST',
        'tool': 'semgrep',
        'files_scanned': len(scanned),
        'scan_errors': len(semgrep_output.get('errors', [])),
        'results': semgrep_output['results'],
    }


def main(input_path, output_path):
    try:
        output_file = resolve_in_work_dir(output_path)
        with open(resolve_in_work_dir(input_path), encoding='utf-8') as f:
            report = consolidate(json.load(f))
    except (OSError, ValueError) as e:
        print(f"[ERROR] SAST scan unusable: {str(e)}")
        return 1

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"[INFO] {len(report['results'])} findings in {report['files_scanned']} files")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))
