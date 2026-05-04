import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Tabloları kontrol et
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=== VERİTABANI TABLOSU ===")
if tables:
    print(f"Toplam {len(tables)} tablo bulundu:\n")
    for t in tables:
        print(f"  - {t[0]}")
else:
    print("Hiç tablo yok - Veritabanı boş!")

# auth_user tablosundaki kullanıcıları kontrol et
try:
    cursor.execute("SELECT COUNT(*) FROM auth_user")
    user_count = cursor.fetchone()[0]
    print(f"\nauth_user tablosunda {user_count} kullanıcı var")
    
    if user_count > 0:
        cursor.execute("SELECT id, username, email, is_staff FROM auth_user")
        for user in cursor.fetchall():
            print(f"  {user[0]}. {user[1]} - {user[2]} (Staff: {bool(user[3])})")
except Exception as e:
    print(f"auth_user tablosu okunamadı: {e}")

conn.close()
