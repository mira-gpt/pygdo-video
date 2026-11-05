"""Keyed layers ordered bottom to top, independent of rendering backend."""


class LayerStack:
    def __init__(self):
        self._layers = {}
        self._sequence = 0

    def put(self, key, layer, z=None):
        if not isinstance(key, str) or not key:
            raise ValueError('Layer key must not be empty')
        previous = self._layers.get(key)
        if z is None:
            z = previous[0] if previous else max((entry[0] for entry in self._layers.values()), default=-1) + 1
        if not isinstance(z, int):
            raise ValueError('Layer z-index must be an integer')
        if previous:
            sequence = previous[1]
        else:
            self._sequence += 1
            sequence = self._sequence
        self._layers[key] = (z, sequence, layer)

    def remove(self, key):
        return self._layers.pop(key, None) is not None

    def get(self, key):
        entry = self._layers.get(key)
        return entry[2] if entry else None

    def clear(self):
        self._layers.clear()

    def ordered(self):
        return [(key, entry[2]) for key, entry in
                sorted(self._layers.items(), key=lambda item: (item[1][0], item[1][1]))]
