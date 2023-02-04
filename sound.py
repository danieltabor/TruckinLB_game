from direct.showbase import DirectObject

sounds = {}

def load(path):
    if path in sounds.keys():
        return sounds[path]
    else:
        sounds[path] = loader.loadSfx(path)
        return sounds[path]
