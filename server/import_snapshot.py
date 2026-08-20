import argparse
from pathlib import Path

from .database import DEFAULT_DATABASE, DEFAULT_SOURCE, import_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a Fabric permission discovery snapshot into SQLite.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    counts = import_snapshot(args.source.resolve(), args.database.resolve())
    print(f"Imported snapshot into {args.database.resolve()}")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()