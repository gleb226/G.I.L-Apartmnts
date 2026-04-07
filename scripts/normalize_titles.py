import asyncio
import os
import sys


def project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


sys.path.append(project_root())

from app.databases.mongodb import apartments_col, export_site_json, refresh_apartments_cache
from app.utils.translator import translate_text


async def main():
    apartments = await apartments_col.find({}).to_list(None)
    updated = 0

    for apartment in apartments:
        address = (apartment.get("address") or "").strip()
        if not address:
            continue

        title_en = await translate_text(address)
        if not title_en or title_en == address:
            title_en = address

        await apartments_col.update_one(
            {"_id": apartment["_id"]},
            {"$set": {"title": {"uk": address, "en": title_en}}},
        )
        updated += 1

    await refresh_apartments_cache()
    await export_site_json()
    print(f"Normalized titles for {updated} apartments.")


if __name__ == "__main__":
    asyncio.run(main())
