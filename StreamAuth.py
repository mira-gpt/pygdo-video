"""Access control for the direct stream; the key is never carried in URLs."""
import base64
import binascii
import hmac

from gdo.base.Application import Application
from gdo.base.GDO_ModuleVal import GDO_ModuleVal
from gdo.video.module_video import module_video


def stream_key():
    table = GDO_ModuleVal.table()
    row = table.get_by_vals({'mv_module': module_video.instance().get_id(), 'mv_key': 'video_gdo_stream_key'})
    return row.gdo_val('mv_val') if row else None


def authorized(key, header, tls):
    if not key:
        return True
    if not tls or not header or not header.lower().startswith('basic '):
        return False
    try:
        encoded = header.split(None, 1)[1]
        if len(encoded) > 2048:
            return False
        decoded = base64.b64decode(encoded, validate=True).decode('utf-8')
        _username, separator, password = decoded.partition(':')
        return bool(separator) and hmac.compare_digest(password.encode('utf-8'), key.encode('utf-8'))
    except (ValueError, IndexError, UnicodeError, binascii.Error):
        return False


def require_stream_access():
    key = stream_key()
    header = Application.get_client_header('HTTP_AUTHORIZATION') or Application.get_client_header('authorization')
    Application.header('Cache-Control', 'no-store, private')
    Application.header('X-Content-Type-Options', 'nosniff')
    if authorized(key, header, Application.is_tls()):
        return True
    if not Application.is_tls():
        Application.status('403 Forbidden')
    else:
        Application.status('401 Unauthorized')
        Application.header('WWW-Authenticate', 'Basic realm="PyGDO live stream", charset="UTF-8"')
    return False
