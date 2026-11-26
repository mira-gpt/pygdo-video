"""Validation and presentation for the desktop WebKit media window."""
import html
import mimetypes
import base64
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password:
        return url
    if parsed.scheme == 'file' and not parsed.netloc and parsed.path.startswith('/') and not parsed.query and not parsed.fragment:
        return url
    raise ValueError('Media URL must use file, http or https')


def youtube_video_id(url):
    """Extract only canonical single-video YouTube links, never lookalike hosts."""
    validate_url(url)
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https'):
        return None
    host = (parsed.hostname or '').lower()
    parts = parsed.path.strip('/').split('/')
    if host == 'youtu.be' and len(parts) == 1:
        video_id = parts[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        if parsed.path == '/watch':
            values = parse_qs(parsed.query).get('v', [])
            video_id = values[0] if len(values) == 1 else ''
        elif len(parts) == 2 and parts[0] in ('embed', 'shorts', 'live'):
            video_id = parts[1]
        else:
            return None
    else:
        return None
    return video_id if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id) else None


def youtube_embed_code(url, autoplay=False):
    video_id = youtube_video_id(url)
    if not video_id:
        raise ValueError('Expected a YouTube single-video URL')
    source = f'https://www.youtube.com/embed/{video_id}?loop=1&amp;playlist={video_id}'
    if autoplay:
        source += '&amp;autoplay=1'
    allow = 'autoplay; encrypted-media; picture-in-picture' if autoplay else 'encrypted-media; picture-in-picture'
    return (f'<iframe width="560" height="315" src="{source}" '
            f'title="YouTube video player" allow="{allow}" '
            'allowfullscreen></iframe>')


def document_for(url, autoplay=False):
    """Wrap recognized media; return None for an ordinary web page."""
    validate_url(url)
    if youtube_video_id(url):
        return ('<!doctype html><meta charset="utf-8"><style>'
                'html,body,iframe{margin:0;width:100%;height:100%;border:0}'
                '</style>' + youtube_embed_code(url, autoplay=autoplay))
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
        autoplay_attr = ' autoplay' if autoplay else ''
        element = f'<video controls loop playsinline{autoplay_attr} src="{source}"></video>'
    elif mime and mime.startswith('image/'):
        element = f'<img src="{source}" alt="">'
    else:
        return None
    return ('<!doctype html><meta charset="utf-8"><style>'
            'html,body{margin:0;width:100%;height:100%;background:transparent}'
            'body{display:flex;align-items:center;justify-content:center}'
            'img,video{max-width:100%;max-height:100%;object-fit:contain}'
            '</style>' + element)
