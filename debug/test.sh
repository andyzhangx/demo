#!/usr/bin/env sh

starting_file_count="$1"

mkdir "test"

echo "Creating '${starting_file_count}' test files..."
for file_index in $(seq 1 "${starting_file_count}"); do
  filename="test/test_${file_index}"
  
  touch "${filename}"
done
echo ""

echo "Trying to delete test files..."

while [ -d "test" ]; do
  count_before=$(ls test/ | wc -l)
  count_deleted=$(rm -vrf test/ 2>/dev/null | wc -l)
  count_after=$( (ls test/ | wc -l) 2>/dev/null || echo 0)

  echo "DELETED: ${count_deleted}  BEFORE: ${count_before}  AFTER: ${count_after}"
done

echo ""

