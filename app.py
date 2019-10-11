"""."""
import logging
import os
from functools import wraps
from uuid import uuid4

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
app.secret_key = 'secret-key'

RESULTS_FOLDER = os.getenv('BIG_FILE_UPLOAD_RESULTS_FOLDER',
                           os.path.join(os.path.dirname(__file__),
                                        'benchmark'))
"""Where to store benchmarking files."""

os.makedirs(RESULTS_FOLDER, exist_ok=True)


def profile(f):
    """Add option to memory profile endpoint."""
    @wraps(f)
    def func(*args, **kwargs):
        profile = request.args.get('profile', False, type=bool)
        if profile:
            import tracemalloc
            import cProfile
            import pstats
            pr = cProfile.Profile()
            pr.enable()
            tracemalloc.start()

        to_return = f(*args, **kwargs)

        if profile:
            file_size = request.headers.get('Content-Length', 'size-not-known')
            upload_type = request.headers.get('Content-Type'
                                              ).split(';')[0].replace('/', '-')
            benchmark_file = f'{upload_type}_{file_size}-bytes.txt'
            with open(os.path.join(RESULTS_FOLDER, benchmark_file), 'w') as ff:
                pr.disable()
                sortby = 'cumulative'
                ff.write('######## Time and calls profiling. ########\n')
                ps = pstats.Stats(pr, stream=ff).sort_stats(sortby)
                ps.print_stats()
                ff.write('########     Memory profiling.     ########\n')
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')
                ff.write("[ Top 10 ]\n")
                for stat in top_stats[:10]:
                    ff.write(f'{stat}\n')
        return to_return
    return func


def write_file_stream_to_dev_null(stream):
    """Write file stream to dev null."""
    try:
        with open(os.devnull, 'wb') as saved_file:
            saved_file.writelines(stream)
            return jsonify({'msg': 'File saved'})
    except Exception as e:
        return jsonify({'msg': 'something went wrong while writing file'})
        logging.error(e.msg, exc_info=True)


def write_file_stream_to_current_dir(stream):
    """Write file stream to dev null."""
    download_dir = os.path.join(os.path.dirname(__file__),
                                'downloads')
    os.makedirs(download_dir, exist_ok=True)
    file_size_in_mb = int(stream.limit/1024/1024)
    filename = f'{file_size_in_mb}MB_{str(uuid4())}'
    file_path = os.path.join(download_dir, filename)
    try:
        with open(file_path, 'wb') as saved_file:
            saved_file.writelines(stream)
            return jsonify({'msg': 'File saved'})
    except Exception as e:
        return jsonify({'msg': 'something went wrong while writing file'})
        logging.error(e.msg, exc_info=True)


@app.route('/request-files', methods=['POST'])
@profile
def upload_request_files():
    """Upload file reading from ``request.files``.

    This is the way we currently implement file uploads because it is the only
    supported way by Bravado, using form data files (more here
    https://github.com/Yelp/bravado/issues/291).

    This is not performant because Werkzeug preprocesses form data (
    https://github.com/pallets/werkzeug/blob/f7374b6bbadefc073def6a2fed85c33784ff1abc/src/werkzeug/formparser.py#L65any)
    and any file bigger than 500 KB is writen to a temporary file,
    more info here
    https://github.com/pallets/werkzeug/blob/f7374b6bbadefc073def6a2fed85c33784ff1abc/src/werkzeug/formparser.py#L53.
    """
    return write_file_stream_to_dev_null(request.files['file'])


@app.route('/request-stream', methods=['POST'])
@profile
def upload_request_stream():
    """Upload file reading directly from ``request.stream``.

    This method used the ``werkzeug.wsgi.LimitedStream``,
    more here https://werkzeug.palletsprojects.com/en/0.15.x/wsgi/#werkzeug.wsgi.LimitedStream,
    which doesn't write any temporary file or to memory, it just directly reads
    from the incoming stream.
    """
    return write_file_stream_to_current_dir(request.stream)


@app.route('/stream-pass-to-next', methods=['POST'])
@profile
def stream_pass_to_next():
    """Mock passing file between "microservices"."""
    next = request.args.get('next', 'localhost:5001')

    class WrappedLimitedStream(object):
        def __init__(self, limitedstream):
            self.limitedstream = limitedstream

        def read(self, *args, **kwargs):
            return self.limitedstream.read(*args, **kwargs)

        def __len__(self):
            return self.limitedstream.limit

    requests.post(f'http://{next}/request-stream',
                  data=WrappedLimitedStream(request.stream),
                  headers={'Content-Type': 'application/octet-stream'})
    return jsonify({'msg': 'File uploaded'})
