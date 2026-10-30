"""Normalize FAT32 directory timestamps after sorted mtools insertion.

The file payload is never changed. VFAT long-name entries are left intact.
"""

import struct
from datetime import UTC, datetime
from pathlib import Path


def normalize_fat_timestamps(image: Path, epoch: int) -> None:
    time = datetime.fromtimestamp(epoch, UTC)
    if not 1980 <= time.year <= 2107:
        raise ValueError("FAT timestamps require a year from 1980 through 2107")
    dos_date = ((time.year - 1980) << 9) | (time.month << 5) | time.day
    dos_time = (time.hour << 11) | (time.minute << 5) | (time.second // 2)
    with image.open("r+b") as stream:
        boot = stream.read(512)
        if boot[510:512] != b"\x55\xaa" or boot[82:90] != b"FAT32   ":
            raise ValueError("Expected an unpartitioned FAT32 image")
        sector_size = struct.unpack_from("<H", boot, 11)[0]
        cluster_sectors = boot[13]
        reserved = struct.unpack_from("<H", boot, 14)[0]
        fat_count = boot[16]
        fat_sectors = struct.unpack_from("<I", boot, 36)[0]
        root_cluster = struct.unpack_from("<I", boot, 44)[0]
        cluster_size = sector_size * cluster_sectors
        fat_offset = sector_size * reserved
        data_offset = sector_size * (reserved + fat_count * fat_sectors)
        total_sectors = struct.unpack_from("<I", boot, 32)[0]
        cluster_limit = (total_sectors * sector_size - data_offset) // cluster_size + 2

        def chain(first):
            visited = set()
            current = first
            while current < 0x0FFFFFF8:
                if current < 2 or current >= cluster_limit or current in visited:
                    raise ValueError("Invalid or cyclic FAT directory cluster chain")
                visited.add(current)
                yield current
                stream.seek(fat_offset + current * 4)
                current = struct.unpack("<I", stream.read(4))[0] & 0x0FFFFFFF

        directories, visited = [root_cluster], set()
        while directories:
            first = directories.pop()
            if first in visited:
                raise ValueError("Directory cycle in image")
            visited.add(first)
            for cluster in chain(first):
                offset = data_offset + (cluster - 2) * cluster_size
                stream.seek(offset)
                block = bytearray(stream.read(cluster_size))
                for entry in range(0, cluster_size, 32):
                    if block[entry] == 0:
                        break
                    attributes = block[entry + 11]
                    if block[entry] == 0xE5 or attributes == 0x0F:
                        continue
                    block[entry + 13] = (time.second % 2) * 100
                    struct.pack_into("<HHH", block, entry + 14, dos_time, dos_date, dos_date)
                    struct.pack_into("<HH", block, entry + 22, dos_time, dos_date)
                    if attributes & 0x10 and block[entry : entry + 1] != b".":
                        high = struct.unpack_from("<H", block, entry + 20)[0]
                        low = struct.unpack_from("<H", block, entry + 26)[0]
                        directories.append((high << 16) | low)
                stream.seek(offset)
                stream.write(block)
