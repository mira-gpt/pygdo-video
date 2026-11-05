"""Small ASCII-safe IPC payloads for the scrolling text effect."""

import base64
import binascii
import zlib

import msgspec.json

from gdo.base.IPC import IPC
from gdo.video.StarWars import StarWars


def encode_text(text):
    StarWars(text)
    payload = base64.b64encode(zlib.compress(text.encode('utf-8'))).decode('ascii')
    if len(msgspec.json.encode([payload])) > IPC.MAX_EVENT_ARG_SIZE:
        raise ValueError('Text is too large for the Dog IPC queue')
    return payload


def decode_text(payload):
    if not isinstance(payload, str) or len(payload) > IPC.MAX_EVENT_ARG_SIZE:
        raise ValueError('Invalid effect payload')
    try:
        compressed = base64.b64decode(payload, validate=True)
        decompressor = zlib.decompressobj()
        data = decompressor.decompress(compressed, StarWars.MAX_LENGTH * 4 + 1)
        if not decompressor.eof or decompressor.unused_data or len(data) > StarWars.MAX_LENGTH * 4:
            raise ValueError('Invalid effect payload')
        text = data.decode('utf-8')
        StarWars(text)
        return text
    except (binascii.Error, zlib.error, UnicodeError) as exc:
        raise ValueError('Invalid effect payload') from exc
