import pickle

def save_cache(cache):
    afile = open('cache.pkl', 'wb')
    pickle.dump(cache, afile)
    afile.close()

def load_cache():
    afile = open('cache.pkl', 'rb')
    cache = pickle.load(afile)
    afile.close()
    return cache
