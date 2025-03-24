cd /out
output=/tmp/fuzzbench/$FUZZER_NAME/$FUZZ_PROJECT/output
mkdir -p $output
PYTHONPATH=$WORK/fuzzbench python3 -u -c "from fuzzers.$FUZZER_NAME import fuzzer; fuzzer.fuzz('/out/seeds', '$output', '/out/fuzz-target')"