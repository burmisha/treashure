import hashlib

def Md5Sum(filename):
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(2 ** 16), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
