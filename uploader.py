import os

import click
import requests

BIG_UPLOAD_SERVER_URL = os.getenv('BIG_UPLOAD_SERVER_URL',
                                  'http://localhost:5000/')

UPLOADER_BY_TYPE = {
    'request.files': lambda file, profile: requests.post(os.path.join(
        BIG_UPLOAD_SERVER_URL, 'request-files'), files={'file': file},
        params={'profile': profile}),
    'request.stream': lambda file, profile: requests.post(os.path.join(
        BIG_UPLOAD_SERVER_URL, 'request-stream'),
        data=file,
        headers={'Content-Type': 'application/octet-stream'},
        params={'profile': profile}),
}
"""Upload types mapping, key is type and value the endpoint."""


@click.command()
@click.argument('file', type=click.File('rb'))
@click.option('-t', '--upload-type',
              type=click.Choice(list(UPLOADER_BY_TYPE.keys()),
                                case_sensitive=False))
@click.option('-p', '--profile',
              is_flag=True)
def upload(file, upload_type, profile):
    """Upload file by chosen upload type."""
    click.echo(f'Uploading {file.name} using {upload_type} ...')
    UPLOADER_BY_TYPE[upload_type](file, profile)
    click.echo(f'File {file.name} uploaded using {upload_type}.')


if __name__ == '__main__':
    upload()
