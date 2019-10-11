# Quick test of large file uploads from Python to Flask app

Problem described in https://github.com/reanahub/reana-client/issues/302.

## Prerequisites

Create a/some big file(s):

```console
$ dd if=/dev/random of=2048MB-file.txt count=2048 bs=1048576
$ ls -lh 2048MB-file.txt
-rw-r--r--  1 username  staff   2.0G Jul  5 11:49 2048MB-file.txt
```

## Local test

### Run the server locally with Flask

Run the Flask application:

```console
$ FLASK_ENV=development FLASK_APP=app.py flask run
...
```

### Upload files of different sizes

In a different window upload big files:

```console
$ ls -lah *-file.txt
-rw-r--r--  1 rodrigdi  staff   256M Oct 10 13:50 256MB-file.txt
-rw-r--r--  1 rodrigdi  staff   512M Oct 10 13:53 512MB-file.txt
-rw-r--r--  1 rodrigdi  staff   1.0G Oct 10 13:55 1GB-file.txt
-rw-r--r--  1 rodrigdi  staff   2.0G Oct 10 13:59 2GB-file.txt
$ python uploader.py [256MB|512MB|1024MB|2048MB]-file.txt \
                      -t [request.stream|request.files] \
                      --profile
Uploading 512MB-file.txt using request.stream ...
File 512MB-file.txt uploaded using request.stream.
$ # Profiling output is written to ./benchmark
$ ls ./benchmark/
application-octet-stream_2147483648bytes.txt
application-octet-stream_1073741824-bytes.txt
application-octet-stream_536870912-bytes.txt
application-octet-stream_268435456-bytes.txt
multipart-form-data_1073741972-bytes.txt
multipart-form-data_536871062-bytes.txt
multipart-form-data_268435606-bytes.txt
```

## Passing file between Flask applications

Start two applications (you will need to terminal sessions):
```console
$ FLASK_ENV=development FLASK_APP=app flask run -p 5001
...
$ FLASK_ENV=development FLASK_APP=app flask run -p 5000
...
```

In a another session stream upload a big file:
```console
$ ipython
with open('2GB-file.txt', 'rb') as f:
    requests.post('http://localhost:5000/stream-pass-to-next',
                  headers={
                      'Content-Type': 'application/octet-stream'},
                  params={'profile': True},
                  data=f)
```

## Closer to production scenario: using Docker and `uwsgi`

Build the server side application and run it in a different terminal session:

```console
$ docker build . -t big-file-upload
$ docker run -ti --rm -p 5000:5000 \
             -v `pwd`/docker-benchmark:/code/benchmark \
             big-file-upload
...
```

Upload the file from your host machine:

```console
$ python uploader.py 2048MB-file.txt -t request.stream --profile
Uploading 2048MB-file.txt using request.stream ...
File 2048MB-file.txt uploaded using request.stream.
$ python uploader.py 2048MB-file.txt -t request.files --profile
Uploading 2048MB-file.txt using request.files ...
File 2048MB-file.txt uploaded using request.files.
```

## Conclusions

Disclaimer: All this tests **do not take into account network overhead**.

| File size     | Method           | Deployment     | Time            |
| :-----------: |:----------------:| :------------: |:---------------:|
| 256 MB        | command `dd`     | bash           | 6.280 seconds   |
| 256 MB        | `request.stream` | Flask          | 5.196 seconds   |
| 256 MB        | `request.files`  | Flask          | 20.431 seconds  |
| 256 MB        | `request.stream` | uwsgi + Docker | 77.104 seconds  |
| 256 MB        | `request.files`  | uwsgi + Docker | 457.781 seconds |
| 512 MB        | command `dd`     | bash           | 12.307 seconds  |
| 512 MB        | `request.stream` | Flask          | 10.323 seconds  |
| 512 MB        | `request.files`  | Flask          | 41.110 seconds  |
| 1 GB          | command `dd`     | bash           | 24.582 seconds  |
| 1 GB          | `request.stream` | Flask          | 21.085 seconds  |
| 1 GB          | `request.files`  | Flask          | 84.105 seconds  |
| 2 GB          | command `dd`     | bash           | 49.426 seconds  |
| 2 GB          | `request.stream` | Flask          | 41.558 seconds  |
| 2 GB          | `request.files`  | Flask          | **crashed**     |

Now, choosing `request.stream`, let's compare differences between:
- **1 Hop**: sending the file to a Flask app and writing it directly to disk
- **2 Hops**: sending the file to a Flask app, which streams it to another Flask app and writes it to disk

| File size | Hops | Time           |
|:---------:|:----:|:--------------:|
| 256MB     | 1    | 5.196 seconds  |
| 256MB     | 2    | 1.611 seconds  |
| 512MB     | 1    | 10.323 seconds |
| 512MB     | 2    | 3.237 seconds  |
| 1GB       | 1    | 21.085 seconds |
| 1GB       | 2    | 6.785 seconds  |
| 2GB       | 1    | 41.558 seconds |
| 2GB       | 2    | 13.426 seconds |

- The `request.files` upload type is taking 4 times the time `request.stream` takes

- We can also observe that in the case of
[`request.files` for a 1GB file](./benchmark/multipart-form-data_1073741972-bytes.txt) most of the time is spent in

    ```
            2    9.804    4.902   78.880   39.440 /Users/rodrigdi/.virtualenvs/big-file-upload-server/lib/python3.6/site-packages/werkzeug/formparser.py:531(parse_parts)
    ```

    This is because `werkzeug` [writes to a tempfile any file bigger that 500KB](https://github.com/pallets/werkzeug/blob/e7ba08f209477cb453f15113f9a4d527a6e81bfe/src/werkzeug/formparser.py#L53-L62).

- There is clearly something that needs to be improved regarding `uwsgi`
configuration.

- Looks like the 2 hops setup is roughly 3x faster. Since this is suspicious, you can check the file integrity (original file versus uploaded file) like follows:
    ```console
    $ bash check-files-integrity.sh
    Removing existing files and downloads ...
    Re-creating new files of sizes: 256MB 512MB 1024MB 2048MB
    256+0 records in
    256+0 records out
    268435456 bytes transferred in 6.280994 secs (42737735 bytes/sec)
    Original file 256MB-file.txt created.
    512+0 records in
    512+0 records out
    536870912 bytes transferred in 12.307863 secs (43620157 bytes/sec)
    Original file 512MB-file.txt created.
    1024+0 records in
    1024+0 records out
    1073741824 bytes transferred in 24.582782 secs (43678613 bytes/sec)
    Original file 1024MB-file.txt created.
    2048+0 records in
    2048+0 records out
    2147483648 bytes transferred in 49.426168 secs (43448314 bytes/sec)
    Original file 2048MB-file.txt created.
    Uploading 256MB file ...
    Uploading 512MB file ...
    Uploading 1024MB file ...
    Uploading 2048MB file ...
    md5(downloads/256MB_0de0d949-6acd-46d2-b02c-aaf86112ba37) -> 76b422e5e525096c2e9c3844e6ae49c0
    md5(256MB-file.txt) -> 76b422e5e525096c2e9c3844e6ae49c0
    256MB - 0
    md5(downloads/512MB_3d6d1acf-6e0c-4799-ad42-9f04f2bde831) -> cf47f19ab9d2e7073741aa4d474e58c2
    md5(512MB-file.txt) -> cf47f19ab9d2e7073741aa4d474e58c2
    512MB - 0
    md5(downloads/1024MB_4242840a-7289-442b-bb55-978a261b9ba1) -> d3d36b9aba3bbd812955983159deb2ed
    md5(1024MB-file.txt) -> d3d36b9aba3bbd812955983159deb2ed
    1024MB - 0
    md5(downloads/2048MB_207b0f69-5971-493e-b52a-0bcc9b076393) -> 2d16f591080ba0fb397743ef8cdbb399
    md5(2048MB-file.txt) -> 2d16f591080ba0fb397743ef8cdbb399
    2048MB - 0
    ```

## **Next**

**On the client side**: Use streaming upload with Requests [as stated in Requests docs](https://requests.kennethreitz.org//en/v1.1.0/user/advanced/#streaming-uploads) with `application/octet-stream` content type:

```python
with open(big_file, 'r') as f:
    request.post('http://localhost/upload-endpoint', data=f,
                 headers={'Content-Type': 'application/octet-stream'})
```

**On the server side**: Use `request.stream` object:
```python
with open(path_to_new_file, 'w') as f:
    f.writelines(request.stream)
```
