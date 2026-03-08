# 💻 Geliştirici Rehberi

Bu rehber, **BookLab** projesine katkıda bulunmak isteyen veya kodu geliştirmek isteyen geliştiriciler için standartları belirler.

## 🛠️ Kod Standartları
- **PEP 8:** Python kodları PEP 8 standartlarına uygun olmalıdır.
- **Docstrings:** Yeni eklenen her fonksiyon ve class için açıklayıcı docstring eklenmelidir.
- **Type Hinting:** Mümkünse fonksiyon parametreleri için tip belirtimi (`name: str`) kullanılmalıdır.

## 🌿 Git Workflow (Branch Yönetimi)
Projede aşağıdaki branch yapısı izlenmelidir:
- `main`: Sadece stabil ve canlıya çıkmaya hazır kodlar.
- `develop`: Geliştirme aşamasındaki özelliklerin birleştiği ana dal.
- `feature/özellik-adı`: Yeni bir özellik eklerken açılacak dal.
- `bugfix/hata-adı`: Hata düzeltmeleri için açılacak dal.

## 🚀 Yeni Özellik Ekleme Adımları
1. Yeni bir feature branch açın.
2. Model değişikliği varsa `makemigrations` yapın.
3. Testlerinizi yerel ortamda (runserver) gerçekleştirin.
4. Kodunuzu `develop` branch'ine PR (Pull Request) olarak gönderin.

---

<div align="center">

| [⬅️ Önceki: Mimari](06_architecture.md) | [Sonraki: SSS ➡️](08_faq.md) |
|:---:|:---:|

</div>

---
<div align="center">
  <sub>BookLab bir <b>Reşit ASRAV</b> projesidir. &copy; 2026</sub>
</div>
