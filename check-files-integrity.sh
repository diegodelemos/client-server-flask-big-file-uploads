#!/bin/bash
file_sizes='256MB 512MB 1024MB 2048MB'

echo "Removing existing files and downloads ..."
rm *-file.txt
rm -rf downloads

echo "Re-creating new files of sizes: $file_sizes"
dd if=/dev/random of=256MB-file.txt count=256 bs=1048576
echo "Original file 256MB-file.txt created."
dd if=/dev/random of=512MB-file.txt count=512 bs=1048576
echo "Original file 512MB-file.txt created."
dd if=/dev/random of=1024MB-file.txt count=1024 bs=1048576
echo "Original file 1024MB-file.txt created."
dd if=/dev/random of=2048MB-file.txt count=2048 bs=1048576
echo "Original file 2048MB-file.txt created."

python - << END
import requests
for size in ['256MB', '512MB', '1024MB', '2048MB']:
    print(f'Uploading {size} file ...')
    with open(f'{size}-file.txt', 'rb') as f:
        requests.post('http://localhost:5000/stream-pass-to-next', headers={'Content-Type': 'application/octet-stream'}, data=f)
END
for size in $file_sizes
do
    original_file="${size}-file.txt"
    original_file_md5=`md5sum ${size}-file.txt | cut -d' ' -f1`
    echo "md5($original_file) -> $original_file_md5"
    uploaded_file=`ls downloads/${size}_*`
    uploaded_file_md5=`md5sum $uploaded_file | cut -d' ' -f1`
    echo "md5($uploaded_file) -> $uploaded_file_md5"
    test "$uploaded_file_md5" = "$original_file_md5"
    echo "${size} - $?"
done
