import os

# Filter Config
# Avanza, 2019-2021, 120jt-190jt, Putih, Manual (Filtered strictly by matcher.py later)
# We use slightly looser search URLs to ensure we don't miss listings with incomplete data.

urls = {
    "MOBIL123_SEARCH_URL": "https://www.mobil123.com/mobil-dijual/toyota/avanza/indonesia?year_min=2019&year_max=2021&price_min=120000000&price_max=190000000",
    "CARMUDI_SEARCH_URL": "https://www.carmudi.co.id/cars/toyota/avanza/?condition=used&year_from=2019&year_to=2021&price_from=120000000&price_to=190000000",
    "JUALO_SEARCH_URL": "https://www.jualo.com/mobil-bekas/toyota+avanza?ob=date&o=desc"
}

env_path = ".env"

def update_env():
    if not os.path.exists(env_path):
        print("Error: File .env tidak ditemukan. Jalankan 'cp .env.example .env' dulu.")
        return

    # Read current content
    with open(env_path, "r") as f:
        content = f.read()

    new_content = content
    print("Mengupdate .env dengan URL baru...")

    for key, url in urls.items():
        # Check if key already exists
        if key in new_content:
            # Replace existing line using basic string replacement (simplest approach)
            # Find the line starting with KEY=
            lines = new_content.splitlines()
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={url}"
            new_content = "\n".join(lines)
        else:
            # Append if not exists
            if not new_content.endswith("\n"):
                new_content += "\n"
            new_content += f"{key}={url}\n"
            
    # Write back
    with open(env_path, "w") as f:
        f.write(new_content)
        
    print("✅ Berhasil! URL Mobil123, Carmudi, dan Jualo telah ditambahkan ke .env")
    print("\nURL yang diset:")
    for k, v in urls.items():
        print(f"- {k}: {v[:50]}...")

if __name__ == "__main__":
    update_env()
