"""Validation and presentation for the desktop WebKit media window."""
import html
import mimetypes
import base64
from pathlib import Path
from urllib.parse import unquote, urlsplit


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password:
        return url
    if parsed.scheme == 'file' and not parsed.netloc and parsed.path.startswith('/') and not parsed.query and not parsed.fragment:
        return url
    raise ValueError('Media URL must use file, http or https')


def document_for(url):
    """Wrap recognized media; return None for an ordinary web page."""
    validate_url(url)
    mime, _ = mimetypes.guess_type(urlsplit(url).path)
    source = url
    if mime and (mime.startswith('video/') or mime.startswith('image/')) and urlsplit(url).scheme == 'file':
        path = Path(unquote(urlsplit(url).path))
        with path.open('rb') as stream:
            data = stream.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('Media file exceeds the size limit')
        source = f'data:{mime};base64,' + base64.b64encode(data).decode('ascii')
    source = html.escape(source, quote=True)
    if mime and mime.startswith('video/'):
        element = f'<video controls loop playsinline src="{source}"></video>'
    elif mime and mime.startswith('image/'):
        element = f'<img src="{source}" alt="">'
    else:
        return None
    return ('<!doctype html><meta charset="utf-8"><style>'
            'html,body{margin:0;width:100%;height:100%;background:transparent}'
            'body{display:flex;align-items:center;justify-content:center}'
            'img,video{max-width:100%;max-height:100%;object-fit:contain}'
            '</style>' + element)
