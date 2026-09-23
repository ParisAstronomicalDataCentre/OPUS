#!/usr/bin/env python3
from urllib.parse import urlparse

from opus_config import CommonSettings

server_name = f"{urlparse(CommonSettings().BASE_URL).netloc}"

def main():
    # 1. Ajoute opus-docker.localhost à /etc/hosts
    hosts_entry = f"127.0.0.1 {server_name}"
    with open("/etc/hosts", "a") as f:
        f.write(f"\n{hosts_entry}\n")

if __name__ == "__main__":
    main()
