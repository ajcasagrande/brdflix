import hashlib
import sys
import time
import os
import zlib

class Hash:
	def __init__(self):
		self.method = None
		self.value = None
		self.filesize = 0L
		self.fullname = None
		self.compute_time = 0.0
		self.mod_time = 0

class CRC32:
    name = 'crc32'
    digest_size = 4
    block_size = 64

    def __init__(self, arg=''):
        self.__hash = 0
        self.update(arg)

    def copy(self):
        return self

    def digest(self):
        return self.__hash & 0xffffffff

    def hexdigest(self):
        return '%08x' % (self.digest())

    def update(self, arg):
        self.__hash = zlib.crc32(arg, self.__hash)

# Add crc32 algorithm
hashlib.crc32 = CRC32
hashlib.algorithms += ('crc32',)

def compute(method, fullname):
	max_bytes = 1073741824L
	start = time.time()
	with open(fullname, 'rb') as f:
		hash = Hash()
		hash.method = method.upper()
		hash.fullname = fullname
		hash.filesize = 0L
		h = None
		if hash.method == 'SHA1':
			h = hashlib.sha1()
		elif hash.method == 'SHA256':
			h = hashlib.sha256()
		elif hash.method == 'MD5':
			h = hashlib.md5()
		elif hash.method == 'CRC32':
			h = hashlib.crc32()
		if h:
			data = f.read(max_bytes)
			while data:
				size = sys.getsizeof(data)
				hash.filesize += size
				print 'Read', size, 'bytes'
				h.update(data)
				data = f.read(max_bytes)
			hash.value = h.hexdigest()
		hash.compute_time = time.time() - start
		return hash
		
def compute_sha1(fullname):
	return compute('SHA1', fullname)
		
def compute_sha256(fullname):
	return compute('SHA256', fullname)
		
def compute_md5(fullname):
	return compute('MD5', fullname)
	
def compute_crc32(fullname):
	return compute('CRC32', fullname)

'''
Super fast hash of file that does not actually read
any data, instead it just hashes the filesize
and last modified date together with the filename.
It may not be the most accurate.
'''
def quick(fullname):
	start = time.time()
	if os.path.isfile(fullname):
		hash = Hash()
		hash.method = 'QUICK'
		hash.fullname = fullname
		hash.filesize = os.path.getsize(fullname)
		hash.mod_time = os.path.getmtime(fullname)
		hash.value = hashlib.sha1(fullname + str(hash.filesize) + str(hash.mod_time)).hexdigest()
		hash.compute_time = time.time() - start
		return hash
	return None
	
if __name__ == "__main__":
	if len(sys.argv) == 2:
		fullname = sys.argv[1]
		if os.path.isfile(fullname):
			# sha1 = compute_sha1(fullname)
			# print "SHA1:", sha1.value
			# print "Completed in:", sha1.compute_time, 'seconds'
			
			# sha256 = compute_sha256(fullname)
			# print "SHA256:", sha256.value
			# print "Completed in:", sha256.compute_time, 'seconds'
		
			# md5 = compute_md5(fullname)
			# print "MD5:", md5.value
			# print "Completed in:", md5.compute_time, 'seconds'
			
			# crc32 = compute_crc32(fullname)
			# print "CRC32:", crc32.value
			# print "Completed in:", crc32.compute_time, 'seconds'
			
			q = quick(fullname)
			print "QUICK:", q.value
			print "Completed in:", q.compute_time, 'seconds'


