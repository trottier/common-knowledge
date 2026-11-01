import { openSync, readSync, fstatSync, closeSync } from "node:fs";

/** PMTiles byte ranges from a local, previously checksum-verified file. */
export class LocalSource {
  constructor(path, checksum) {
    this.descriptor = openSync(path, "r");
    this.size = fstatSync(this.descriptor).size;
    this.key = checksum;
  }

  getKey() {
    return this.key;
  }

  async getBytes(offset, length) {
    if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(length) ||
        offset < 0 || length < 0 || offset > this.size) {
      throw new Error("Invalid local PMTiles byte range");
    }
    const count = Math.min(length, this.size - offset);
    const data = Buffer.alloc(count);
    let read = 0;
    while (read < count) {
      const current = readSync(this.descriptor, data, read, count - read, offset + read);
      if (!current) throw new Error("Truncated local PMTiles input");
      read += current;
    }
    return { data: data.buffer.slice(data.byteOffset, data.byteOffset + count), etag: this.key };
  }

  close() {
    closeSync(this.descriptor);
  }
}

export function resource(url) {
  const tile = /^ck-tile:\/\/(\d+)\/(\d+)\/(\d+)$/.exec(url);
  if (tile) {
    const [z, x, y] = tile.slice(1).map(Number);
    if (z > 24 || x >= 2 ** z || y >= 2 ** z) throw new Error("Invalid tile coordinates");
    return { kind: "tile", z, x, y };
  }
  const glyph = /^ck-font:\/\/[^/]+\/(\d+)-(\d+)\.pbf$/.exec(url);
  if (glyph) {
    const start = Number(glyph[1]);
    const end = Number(glyph[2]);
    if (start % 256 || end !== start + 255 || end > 65535) {
      throw new Error("Invalid glyph range");
    }
    return { kind: "glyph", start, end };
  }
  throw new Error(`Resource outside the offline atlas inputs: ${url}`);
}
