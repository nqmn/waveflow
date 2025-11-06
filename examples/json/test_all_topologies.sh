#!/bin/bash
################################################################################
# Test all JSON topologies
#
# This script loads and verifies all 7 JSON topologies can be loaded without error
#
# Usage:
#   bash test_all_topologies.sh
#   or
#   ./test_all_topologies.sh
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "================================================================================"
echo "RISNet JSON Topologies Test Suite"
echo "================================================================================"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

TOPOLOGIES=(
  "example_1_simple.json"
  "example_2_predefined_topology.json"
  "example_3_custom_topology.json"
  "example_4_obstacles.json"
  "example_5_grid_topology.json"
  "example_6_batch_testing.json"
  "example_7_complex_network.json"
)

PASSED=0
FAILED=0

for topo in "${TOPOLOGIES[@]}"; do
  echo -n "Testing: $topo ... "

  if python3 main.py --topology "examples/json_topologies/$topo" list > /dev/null 2>&1; then
    echo "✓ PASS"
    ((PASSED++))
  else
    echo "✗ FAIL"
    ((FAILED++))
  fi
done

echo ""
echo "================================================================================"
echo "Test Results"
echo "================================================================================"
echo "  Total Topologies: ${#TOPOLOGIES[@]}"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
  echo "✓ All topologies loaded successfully!"
  exit 0
else
  echo "✗ Some topologies failed to load"
  exit 1
fi
