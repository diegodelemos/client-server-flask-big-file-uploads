# Large file upload to Flask from Python client

Problem described in https://github.com/reanahub/reana-client/issues/302.

## Prerequisites

Create a/some big file(s):

```console
$ dd if=/dev/random of=2GB-file.txt count=2048 bs=1048576
$ ls -lh 2GB-file.txt
-rw-r--r--  1 username  staff   2.0G Jul  5 11:49 2GB-file.txt
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
$ python uploader.py [256MB|512MB|1GB]-file.txt \
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
$ python uploader.py 2GB-file.txt -t request.stream --profile
Uploading 2GB-file.txt using request.stream ...
File 2GB-file.txt uploaded using request.stream.
$ python uploader.py 2GB-file.txt -t request.files --profile
Uploading 2GB-file.txt using request.files ...
File 2GB-file.txt uploaded using request.files.
```

## Conclusions

| File size     | Method           | Deployment     | Time            |
| :-----------: |:----------------:| :------------: |:--------------:|
| 256 MB        | `request.stream` | Flask          | 5.196 seconds   |
| 256 MB        | `request.stream` | uwsgi + Docker | 77.104 seconds  |
| 512 MB        | `request.stream` | Flask          | 10.323 seconds  |
| 1 GB          | `request.stream` | Flask          | 21.085 seconds  |
| 2 GB          | `request.stream` | Flask          | 41.558 seconds  |
| 256 MB        | `request.files`  | Flask          | 20.431 seconds  |
| 256 MB        | `request.files`  | uwsgi + Docker | 457.781 seconds |
| 512 MB        | `request.files`  | Flask          | 41.110 seconds  |
| 1 GB          | `request.files`  | Flask          | 84.105 seconds  |
| 2 GB          | `request.files`  | Flask          | **crashed**     |

- The `request.files` upload type is taking 4 times the time `request.stream` takes

- We can also observe that in the case of
[`request.files` for a 1GB file](./benchmark/multipart-form-data_1073741972-bytes.txt) most of the time is spent in

    ```
            2    9.804    4.902   78.880   39.440 /Users/rodrigdi/.virtualenvs/big-file-upload-server/lib/python3.6/site-packages/werkzeug/formparser.py:531(parse_parts)
    ```

    This is because `werkzeug` [writes to a tempfile any file bigger that 500KB](https://github.com/pallets/werkzeug/blob/e7ba08f209477cb453f15113f9a4d527a6e81bfe/src/werkzeug/formparser.py#L53-L62).

- There is clearly something that needs to be improved regarding `uwsgi`
configuration.

## **Solution**

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
