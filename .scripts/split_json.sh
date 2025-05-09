#!/bin/bash

# Usage: ./split_data_list_fast.sh input.json output-prefix [max-size-mb]
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 input.json output-prefix [max-size-mb]"
  exit 1
fi

INPUT_FILE=$1
MAX_SIZE=${2:-100} # Default to 100MB if not specified
MAX_SIZE_BYTES=$((MAX_SIZE * 1024 * 1024))
OUTPUT_DIR=$(dirname "$INPUT_FILE")
OUTPUT_PREFIX=$(basename "$INPUT_FILE" .json)

# Verify the input is valid JSON
echo "Verifying input file structure..."
if ! jq -e 'has("data_list")' "$INPUT_FILE" > /dev/null 2>&1; then
  echo "Error: Input file doesn't have data_list structure"
  exit 1
fi

# Faster approach: use jq to create pre-sized chunks in one pass
echo "Analyzing file and determining chunk sizes..."

# Get total element count and estimate size per element
TOTAL_ELEMENTS=$(jq -r '.data_list | length' "$INPUT_FILE")
FILE_SIZE=$(stat -c%s "$INPUT_FILE")
EMPTY_SIZE=$(echo '{"data_list":[]}' | wc -c)
DATA_SIZE=$((FILE_SIZE - EMPTY_SIZE))
AVG_ELEMENT_SIZE=$((DATA_SIZE / TOTAL_ELEMENTS))

# Calculate safe number of elements per chunk
ELEMENTS_PER_CHUNK=$((MAX_SIZE_BYTES * 80 / 100 / AVG_ELEMENT_SIZE)) # 80% safety margin
if [ $ELEMENTS_PER_CHUNK -lt 1 ]; then
  ELEMENTS_PER_CHUNK=1
fi

echo "Input file: $(basename "$INPUT_FILE") (${FILE_SIZE} bytes, $TOTAL_ELEMENTS elements)"
echo "Average element size: $AVG_ELEMENT_SIZE bytes"
echo "Using approximately $ELEMENTS_PER_CHUNK elements per chunk"

# Create chunks in a single efficient pass
COUNTER=0
TOTAL_CHUNKS=$(((TOTAL_ELEMENTS + ELEMENTS_PER_CHUNK - 1) / ELEMENTS_PER_CHUNK))
echo "Creating approximately $TOTAL_CHUNKS chunks..."

# Use process substitution to avoid temp files and maximize throughput
for ((i=0; i<TOTAL_ELEMENTS; i+=ELEMENTS_PER_CHUNK)); do
  END=$((i + ELEMENTS_PER_CHUNK))
  if [ $END -gt $TOTAL_ELEMENTS ]; then
    END=$TOTAL_ELEMENTS
  fi

  OUTFILE="${OUTPUT_DIR}/${OUTPUT_PREFIX}_${COUNTER}.json"

  echo -ne "Creating chunk $COUNTER/$TOTAL_CHUNKS ($((i+1))-$END of $TOTAL_ELEMENTS elements)...\r"

  # Extract chunk directly to output file in one operation
  jq "{\"data_list\": .data_list[$i:$END]}" "$INPUT_FILE" > "$OUTFILE"

  COUNTER=$((COUNTER + 1))
done

echo -e "\nSplit complete. Created $COUNTER files."
