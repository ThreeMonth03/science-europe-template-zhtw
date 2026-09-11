"""Stage a validated candidate locally. This does not publish a GitHub release."""

import argparse
from pathlib import Path

from artifact_utils import stage_candidate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    args = parser.parse_args()
    print(stage_candidate(args.build, args.store))
