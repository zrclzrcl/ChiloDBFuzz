"""
AFL++ Coverage Bitmap Reader for Python Custom Mutators

This module allows Python custom mutators to read the coverage bitmap
from AFL++'s shared memory, enabling access to edge coverage information.
"""

import os
import sys
import ctypes
from ctypes import c_void_p, c_int, POINTER, c_uint8, c_char_p

# Constants
SHM_ENV_VAR = "__AFL_SHM_ID"


# Try to get map size from environment (AFL++ may set this)

MAP_SIZE = int(os.environ.get("AFL_MAP_SIZE"))



class AFLCoverageReader:
    """Reads AFL++ coverage bitmap from shared memory"""
    
    def __init__(self):
        self.shm_id = None
        self.map_ptr = None
        self.map_size = MAP_SIZE
        self._libc = None
        self._attached = False
        self._init_libc()
        # Defer attaching to shared memory until first use
    
    def _ensure_attached(self):
        """Attach to shared memory on first access"""
        if not self._attached:
            self._attach_shm()
            self._attached = True
    
    def _init_libc(self):
        """Initialize libc for system calls"""
        if sys.platform == "win32":
            # Windows: Use kernel32 for shared memory
            self._libc = ctypes.CDLL("kernel32.dll", use_errno=True)
            # Note: Windows support may need different approach
            raise NotImplementedError(
                "Windows support for AFL++ shared memory requires different implementation. "
                "Consider using WSL or Linux for fuzzing."
            )
        else:
            # Linux/Unix: Use libc
            try:
                self._libc = ctypes.CDLL("libc.so.6", use_errno=True)
            except OSError:
                try:
                    self._libc = ctypes.CDLL("libc.dylib", use_errno=True)  # macOS
                except OSError:
                    raise RuntimeError("Cannot load libc. Unsupported platform.")
    
    def _attach_shm(self):
        """Attach to AFL++ shared memory segment"""
        # Get shared memory identifier from environment variable
        SHM_ENV_VAR_VALUE = input("请输入AFL++中SHM_ENV_VAR的值:")
        shm_id_str = SHM_ENV_VAR_VALUE
        if not shm_id_str:
            raise RuntimeError(
                f"Environment variable {SHM_ENV_VAR} not set. "
                "This module should only be used within AFL++ custom mutator context."
            )
        
        if sys.platform == "win32":
            raise NotImplementedError(
                "Windows support for AFL++ shared memory requires different implementation. "
                "Consider using WSL or Linux for fuzzing."
            )
        
        # AFL++ can use two modes:
        # 1. USEMMAP mode: __AFL_SHM_ID contains a file path (e.g., "/afl_12345_67890")
        # 2. Traditional mode: __AFL_SHM_ID contains a numeric shmid
        
        if shm_id_str.startswith('/'):
            # USEMMAP mode: use shm_open + mmap
            self._attach_shm_mmap(shm_id_str)
        else:
            # Traditional mode: use shmat
            self._attach_shm_traditional(shm_id_str)
    
    def _attach_shm_mmap(self, shm_path):
        """Attach using mmap (USEMMAP mode)"""
        # Setup shm_open
        self._libc.shm_open.argtypes = [c_char_p, c_int, c_int]
        self._libc.shm_open.restype = c_int
        
        # Setup mmap
        # Use appropriate types for size_t and off_t
        if sys.platform == "darwin":  # macOS
            size_t = ctypes.c_ulonglong
            off_t = ctypes.c_longlong
        else:  # Linux
            size_t = ctypes.c_size_t
            off_t = ctypes.c_long
        self._libc.mmap.argtypes = [c_void_p, size_t, c_int, c_int, c_int, off_t]
        self._libc.mmap.restype = c_void_p
        
        # Setup close
        self._libc.close.argtypes = [c_int]
        self._libc.close.restype = c_int
        
        # Open shared memory object
        O_RDONLY = 0o0
        shm_fd = self._libc.shm_open(shm_path.encode('utf-8'), O_RDONLY, 0o644)
        if shm_fd == -1:
            errno = ctypes.get_errno()
            raise RuntimeError(
                f"shm_open() failed for {shm_path} with errno {errno}. "
                "Make sure AFL++ is running and shared memory is accessible."
            )
        
        # Map the shared memory
        PROT_READ = 0x1
        MAP_SHARED = 0x01
        MAP_FAILED = c_void_p(-1)
        
        self.map_ptr = self._libc.mmap(
            None, self.map_size, PROT_READ, MAP_SHARED, shm_fd, 0
        )
        
        # Close the file descriptor (mmap keeps the mapping)
        self._libc.close(shm_fd)
        
        if self.map_ptr == MAP_FAILED or self.map_ptr is None:
            errno = ctypes.get_errno()
            raise RuntimeError(
                f"mmap() failed with errno {errno}. "
                "Make sure AFL++ is running and shared memory is accessible."
            )
    
    def _attach_shm_traditional(self, shm_id_str):
        """Attach using traditional shmat (System V IPC)"""
        try:
            self.shm_id = int(shm_id_str)
        except ValueError:
            raise RuntimeError(f"Invalid {SHM_ENV_VAR} value: {shm_id_str}")
        
        # Setup shmat function
        self._libc.shmat.argtypes = [c_int, c_void_p, c_int]
        self._libc.shmat.restype = c_void_p
        
        # Attach to shared memory (IPC_PRIVATE mode, read-only)
        # shmat(shmid, NULL, SHM_RDONLY)
        SHM_RDONLY = 0x10000  # Read-only flag
        self.map_ptr = self._libc.shmat(self.shm_id, None, SHM_RDONLY)
        
        if self.map_ptr == -1 or self.map_ptr is None:
            errno = ctypes.get_errno()
            raise RuntimeError(
                f"shmat() failed with errno {errno}. "
                "Make sure AFL++ is running and shared memory is accessible."
            )
    
    def get_coverage_bitmap(self):
        """
        Get the coverage bitmap as a bytes object
        
        Returns:
            bytes: Coverage bitmap (typically 65536 bytes)
        """
        self._ensure_attached()
        if self.map_ptr is None or self.map_ptr == -1:
            raise RuntimeError("Shared memory not attached")
        
        # Create a ctypes array view of the shared memory
        array_type = c_uint8 * self.map_size
        bitmap_array = ctypes.cast(self.map_ptr, POINTER(array_type)).contents
        
        # Convert to bytes
        return bytes(bitmap_array)
    
    def get_coverage_count(self):
        """
        Count the number of edges hit (non-zero entries in bitmap)
        
        Returns:
            int: Number of unique edges covered
        """
        bitmap = self.get_coverage_bitmap()
        return sum(1 for b in bitmap if b > 0)
    
    def get_coverage_hash(self):
        """
        Get a hash of the coverage bitmap (useful for comparing coverage)
        
        Returns:
            int: Hash value of the coverage bitmap
        """
        import hashlib
        bitmap = self.get_coverage_bitmap()
        return int(hashlib.md5(bitmap).hexdigest()[:8], 16)
    
    def compare_coverage(self, previous_bitmap):
        """
        Compare current coverage with previous coverage
        
        Args:
            previous_bitmap: Previous coverage bitmap (bytes)
        
        Returns:
            tuple: (new_edges_count, total_edges_count)
                - new_edges_count: Number of newly discovered edges
                - total_edges_count: Total number of edges in current run
        """
        current = self.get_coverage_bitmap()
        if len(current) != len(previous_bitmap):
            raise ValueError("Bitmap sizes don't match")
        
        new_edges = 0
        total_edges = 0
        
        for i in range(len(current)):
            if current[i] > 0:
                total_edges += 1
                if previous_bitmap[i] == 0:
                    new_edges += 1
        
        return new_edges, total_edges
    
    def cleanup(self):
        """Detach from shared memory (optional, Python will handle cleanup)"""
        if self.map_ptr and sys.platform != "win32":
            # For mmap mode, use munmap; for traditional mode, use shmdt
            shm_id_str = os.environ.get(SHM_ENV_VAR, "")
            if shm_id_str.startswith('/'):
                # mmap mode: use munmap
                if sys.platform == "darwin":  # macOS
                    size_t = ctypes.c_ulonglong
                else:  # Linux
                    size_t = ctypes.c_size_t
                self._libc.munmap.argtypes = [c_void_p, size_t]
                self._libc.munmap.restype = c_int
                self._libc.munmap(self.map_ptr, self.map_size)
            else:
                # Traditional mode: use shmdt
                self._libc.shmdt.argtypes = [c_void_p]
                self._libc.shmdt.restype = c_int
                self._libc.shmdt(self.map_ptr)
            self.map_ptr = None


# Global instance (lazy initialization)
_coverage_reader = None


def get_coverage_reader():
    """
    Get or create the global coverage reader instance
    
    Returns:
        AFLCoverageReader: The coverage reader instance
    """
    global _coverage_reader
    if _coverage_reader is None:
        _coverage_reader = AFLCoverageReader()
    return _coverage_reader


def get_coverage_bitmap():
    """Convenience function to get coverage bitmap"""
    return get_coverage_reader().get_coverage_bitmap()


def get_coverage_count():
    """Convenience function to get coverage count"""
    return get_coverage_reader().get_coverage_count()


def get_new_coverage(previous_bitmap):
    """
    Get new coverage compared to previous bitmap
    
    Args:
        previous_bitmap: Previous coverage bitmap (bytes) or None
    
    Returns:
        tuple: (new_edges_count, current_bitmap)
    """
    reader = get_coverage_reader()
    current = reader.get_coverage_bitmap()
    
    if previous_bitmap is None:
        return reader.get_coverage_count(), current
    
    new_edges, _ = reader.compare_coverage(previous_bitmap)
    return new_edges, current

