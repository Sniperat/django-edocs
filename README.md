# django-edocs

[![PyPI version](https://img.shields.io/pypi/v/django-edocs.svg)](https://pypi.org/project/django-edocs/)
[![Python](https://img.shields.io/pypi/pyversions/django-edocs.svg)](https://pypi.org/project/django-edocs/)
[![Django](https://img.shields.io/badge/django-4.2%20%7C%205.0%20%7C%205.1%20%7C%205.2-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**django-edocs** — Django loyihalari uchun professional elektron hujjat generatsiyasi, Word (`.docx`) shablon dvijogi, dinamik jadvallar, PDF konvertatsiyasi, QR-kodli tekshiruv va E-IMZO orqali ko'p tomonlama imzolash ish jarayoni (workflow) tizimi.

---

## 🌟 Asosiy Imkoniyatlar (Features)

1. **Smart Word (.docx) Shablon Dvijogi**:
   * Jinja2 (`{{ var }}`) hamda rasmiy davlat shartnomalaridagi dollar-skobka (`${var}`) sintaksislarini to'liq qo'llab-quvvatlaydi.
   * Microsoft Word matnni bo'lib yuborgan holatlarda XML teglarni avtomatik tuzatadi va ulaydi.
   * **Dinamik jadvallar (Auto Table Loops)**: Jadvaldagi `{{ items.name }}` yoki `${items.name}` o'zgaruvchilarini avtomatik aniqlab, qatorlarni takrorlanuvchi tsiklga o'raydi.
   * `None` yoki `"null"` qiymatlarni avtomatik bo'sh qatorga (`""`) aylantiradi.

2. **PDF Konvertatsiya va QR-Kodli Xavfsizlik**:
   * Word fayllarini avtomatik tarzda yuqori sifatli PDF formatiga o'tkazadi (headless LibreOffice orqali).
   * Har bir hujjatga takrorlanmas **4 xonali xavfsizlik kodi** va **SHA-256 hesh** biriktiriladi.
   * Hujjatning pastki yoki burchak qismiga vertikal kodli dinamik **QR-kod** generatsiya qilinadi.

3. **Ko'p Bosqichli E-IMZO Imzolash Ketma-ketligi**:
   * Ketma-ket imzolash navbati (masalan: 1-tomon -> 2-tomon -> 3-tomon).
   * Navbat kelmaguncha keyingi shaxs imzo qo'ya olmaydi.
   * Hujjatni ko'rish, imzolash, **Rad etish** (izoh bilan) va **Bekor qilish** imkoniyati.

4. **Tayyor REST API & Brauzer E-IMZO Mijozi**:
   * Django REST Framework uchun tayyor Challenge, Sign, Reject, Cancel va PDF Preview endpointlari.
   * Brauzerdagi mahalliy E-IMZO moduli (port 64443) bilan ishlovchi tayyor `eimzo-client.js` kutubxonasi.
   * QR-kod skaner qilinganda mobil qurilmalarda ochiluvchi chiroyli ommaviy tekshiruv sahifasi.

---

## 📦 O'rnatish (Installation)

```bash
pip install django-edocs
```

Tizimda Word fayllarni PDF ga o'girish uchun LibreOffice o'rnatilgan bo'lishi kerak:
```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y libreoffice fonts-dejavu

# Dockerfile uchun
RUN apt-get update && apt-get install -y libreoffice fonts-dejavu && rm -rf /var/lib/apt/lists/*
```

---

## 🚀 Tezkor Boshlash (Quickstart)

### 1. `settings.py` sozlamalari

`INSTALLED_APPS` ro'yxatiga `'edocs'` va `'rest_framework'` ni qo'shing:

```python
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'edocs',
    # ...
]
```

Ixtiyoriy sozlamalar:
```python
# settings.py
EDOCS_VERIFY_FRONTEND_URL = "https://myportal.uz/edocs/verify" # QR kod skaner qilinganda yo'naltiriladigan URL
EDOCS_LIBREOFFICE_PATH = "libreoffice" # yoki "/usr/bin/libreoffice"
EDOCS_SIGNER_MODEL = "auth.User" # yoki o'zingizning maxsus xodim/rol modelingiz
```

### 2. Ma'lumotlar bazasini yangilang

```bash
python manage.py migrate
```

### 3. URL marshrutlarini ulang

Loyiha `urls.py` fayliga:

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path("api/edocs/", include("edocs.api.urls")),
    # ...
]
```

### 4. O'z modelingizga hujjat biriktirish

Shartnoma, dalolatnoma yoki ma'lumotnoma modelingizni `AbstractDocumentBase` dan meros qilib oling:

```python
from django.db import models
from edocs.models import AbstractDocumentBase

class Contract(AbstractDocumentBase):
    number = models.CharField(max_length=50)
    client_name = models.CharField(max_length=255)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Shartnoma #{self.number}"
```

### 5. Hujjat generatsiya qilish

```python
from edocs.services import DocumentEngine
from myapp.models import Contract

# 1. Shartnomani saqlash
contract = Contract.objects.create(
    number="12/2026",
    client_name="Agro Tech MCHJ",
    total_amount=50000000
)

# 2. Hujjatni Word shabloni asosida generatsiya qilish
document = DocumentEngine.generate_document(
    template_code="standard_contract",
    context_data={
        "contract_number": contract.number,
        "client_name": contract.client_name,
        "total_amount": str(contract.total_amount),
        "items": [
            {"num": 1, "name": "Mahsulot A", "qty": 10, "price": "2000000"},
            {"num": 2, "name": "Mahsulot B", "qty": 5, "price": "6000000"},
        ]
    },
    related_object=contract,
    signers=[
        {"signer": user_director, "title": "Direktor", "tin": "123456789"},
        {"signer": user_client, "title": "Haridor", "tin": "987654321"},
    ]
)

# 3. Hujjatni shartnomaga biriktirish
contract.document = document
contract.save()
```

---

## 🔑 Brauzerda E-IMZO bilan imzolash (Frontend)

Paket ichida tayyor `eimzo-client.js` mavjud:

```html
<script src="/static/edocs/js/eimzo-client.js"></script>
<script>
  // 1. E-IMZO moduli ochiqligini tekshirish
  EImzoClient.checkAgent().then(isOnline => {
    if (!isOnline) {
      alert("Iltimos, E-IMZO dasturini ishga tushiring!");
      return;
    }

    // 2. Sertifikatlar ro'yxatini olish
    EImzoClient.listCertificates().then(certs => {
      console.log("Mavjud kalitlar:", certs);
      
      // 3. Tanlangan kalit bilan hujjatni imzolash
      const chosenCert = certs[0];
      EImzoClient.signDocument("DOCUMENT-GUID-HERE", chosenCert)
        .then(res => {
          alert("Hujjat muvaffaqiyatli imzolandi!");
          window.location.reload();
        })
        .catch(err => alert("Xatolik: " + err.message));
    });
  });
</script>
```

---

## 📡 Signallar (Signals)

Hujjat holati o'zgarganda bildirishnoma (Telegram bot, SMS, WebSocket) yuborish uchun Django signallaridan foydalaning:

```python
from django.dispatch import receiver
from edocs.signals import document_fully_signed, document_rejected

@receiver(document_fully_signed)
def on_document_fully_signed(sender, document, related_object, **kwargs):
    print(f"Hujjat to'liq imzolandi: {document.guid}, Obyekt: {related_object}")

@receiver(document_rejected)
def on_document_rejected(sender, document, signer, note, related_object, **kwargs):
    print(f"Hujjat rad etildi! Sabab: {note}")
```

---

## 📄 Litsenziya (License)

Ushbu kutubxona [MIT License](LICENSE) asosida ochiq manbali tarzda tarqatiladi.
