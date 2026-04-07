import asyncio
import os
import sys


IMAGE_URL = "https://images.unsplash.com/photo-1556784344-ad913c73cfc4?q=80&w=1169&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"


def project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


sys.path.append(project_root())

from app.databases.mongodb import apartments_col, export_site_json, refresh_apartments_cache


async def main():
    result = await apartments_col.update_many(
        {},
        {"$set": {"img": IMAGE_URL, "gallery": [IMAGE_URL]}},
    )
    await refresh_apartments_cache()
    await export_site_json()
    print(f"Updated images for {result.modified_count} apartments.")


if __name__ == "__main__":
    asyncio.run(main())
