"""Resume a large provisional publisher input; this does not certify its hash."""

import argparse
import fcntl
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--item", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-mib", type=int, default=32)
    args = parser.parse_args()
    items = json.loads(args.catalog.read_text())
    item = next(item for item in items if item["id"] == args.item)
    url, size = item["url"], item["size_bytes"]
    if not url.startswith("https://") or type(size) is not int or size <= 0:
        raise ValueError("A confirmed HTTPS URL and publisher byte size are required")
    if not 1 <= args.chunk_mib <= 256:
        raise ValueError("Chunk size must be between 1 and 256 MiB")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    state_path = args.output.with_name(args.output.name + ".state.json")
    state = (
        json.loads(state_path.read_text())
        if state_path.exists()
        else {
            "url": url,
            "size_bytes": size,
            "etag": None,
        }
    )
    if state["url"] != url or state["size_bytes"] != size:
        raise ValueError("Provisional source changed; choose a new output file")
    with args.output.with_name(args.output.name + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with args.output.open("ab") as target:
            offset = target.tell()
            if offset > size:
                raise ValueError("Partial download exceeds the publisher's byte size")
            reported = offset // (1024**3)
            while offset < size:
                end = min(size, offset + args.chunk_mib * 1024**2) - 1
                headers = {
                    "Range": f"bytes={offset}-{end}",
                    "Accept-Encoding": "identity",
                    "User-Agent": "Mozilla/5.0 (compatible; Common-Knowledge/0.1; "
                    "+https://github.com/trottier/common-knowledge)",
                }
                if state["etag"] and not state["etag"].startswith("W/"):
                    headers["If-Range"] = state["etag"]
                for attempt in range(6):
                    try:
                        with urlopen(Request(url, headers=headers), timeout=90) as response:
                            if not response.geturl().startswith("https://"):
                                raise ValueError("Publisher redirected outside HTTPS")
                            if response.status != 206 or response.headers.get("Content-Range") != (
                                f"bytes {offset}-{end}/{size}"
                            ):
                                raise ValueError("Publisher range or source size changed")
                            etag = response.headers.get("ETag")
                            if state["etag"] and etag != state["etag"]:
                                raise ValueError("Publisher source changed during download")
                            payload = response.read(end - offset + 2)
                            if len(payload) != end - offset + 1:
                                raise OSError("Incomplete publisher byte range")
                        break
                    except (OSError, TimeoutError) as error:
                        if (
                            isinstance(error, HTTPError)
                            and error.code not in {408, 429}
                            and error.code < 500
                        ):
                            raise
                        if attempt == 5:
                            raise
                        print(f"Retrying byte {offset}: {error}", flush=True)
                        time.sleep(min(30, 2 ** (attempt + 1)))
                # A chunk is appended only after its whole response is checked.
                target.write(payload)
                target.flush()
                offset = end + 1
                state["etag"] = etag
                state_path.write_text(json.dumps(state, sort_keys=True) + "\n")
                if offset // (1024**3) > reported:
                    reported = offset // (1024**3)
                    print(f"Downloaded {offset:,} / {size:,} bytes", flush=True)
    print("Transfer complete. Verify publisher checksum and SHA-256 before pinning.", flush=True)


if __name__ == "__main__":
    main()
