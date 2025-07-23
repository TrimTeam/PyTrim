import argparse
import os

from pycg_producer.app_producer import CallGraphGenerator


def parse_args():
    parser = argparse.ArgumentParser(description="Produce partial call graph of apps")
    parser.add_argument(
        "-src", "--source", required=True, help="Directory hosting source files"
    )
    return parser.parse_args()


def process(package, source):
    package = package.strip()
    generator = CallGraphGenerator(source, package)
    output = generator.generate()
    return output


def main():
    args = parse_args()
    app = os.path.basename(args.source.strip("/"))
    process(app, args.source)


if __name__ == "__main__":
    main()
