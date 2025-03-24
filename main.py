from logger import logger

import argparse
from utils import compression_work_dir_code
from config import SHARED_DIR
from runDocker import run_docker_fuzz, run_docker_build

def main():
    logger.info("start test")
    parser = argparse.ArgumentParser(description='Open source fuzzbench')
    parser.add_argument("-f", "--fuzzers", nargs='+', type=str, required=False, default=[], help="fuzzers list")
    parser.add_argument("-t", "--fuzz_targets", nargs='+', type=str, required=False, default=[], help="fuzz target project names")
    parser.add_argument("-c", "--cpus", type=int, required=False, default=2, help="Number of CPUs. Number is a fractional number. 0.000 means no limit.")
    parser.add_argument("-m", "--memory", type=str, required=False, default="2G", help="Memory limit (format: <number>[<unit>]). Number is a positive integer. Unit can be one of b, k, m, or g. Minimum is 6M.")

    parser.add_argument("-b", "--build", action='store_true', help="build images")
    parser.add_argument("-r", "--run", action='store_true', help="run experiments")
    parser.add_argument("-re", "--rebuild", action='store_true', help="rebuild images")

    args, _ = parser.parse_known_args()
    if len(args.fuzzers) == 0:
        logger.info("Please input fuzzer")
        parser.print_help()
        return 1

    if len(args.fuzz_targets) == 0:
        logger.info("Please input fuzz target projects")
        parser.print_help()
        return 1

    compression_work_dir_code()

    if args.build:
        run_docker_build(args.fuzzers, args.fuzz_targets, args.build)

    if args.run:
        run_docker_fuzz(args.fuzzers, args.fuzz_targets, args.cpus, args.memory)

    logger.info("Fuzzbench run end.")


if __name__ == "__main__":
    main()
