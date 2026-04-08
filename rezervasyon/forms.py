from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Profil, Ariza

# --- CUSTOM LOGIN FORMU ---
class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Kullanıcı Adı veya E-Posta",
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'Kullanıcı adı veya e-posta'
        })
    )
    password = forms.CharField(
        label="Şifre",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-control',
            'placeholder': '******'
        }),
    )

# --- ÖZEL VALİDATÖR ---
sadece_rakam_validator = RegexValidator(
    regex=r"^\d+$",
    message="Lütfen sadece rakam giriniz.",
)

# --- KAYIT FORMU ---
class KayitFormu(forms.ModelForm):
    username = forms.CharField(
        label="Kullanıcı Adı",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Kullanıcı adınızı seçin"})
    )
    first_name = forms.CharField(
        label="Adınız",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Adınız"})
    )
    last_name = forms.CharField(
        label="Soyadınız",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Soyadınız"})
    )
    email = forms.EmailField(
        label="E-Posta Adresi",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "ornek@mail.com"})
    )

    # ❌ okul_numarasi KALDIRILDI

    telefon = forms.CharField(
        label="Telefon Numarası",
        required=True,
        validators=[sadece_rakam_validator],
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "05551112233",
            "maxlength": "11"
        }),
        help_text="Başında 0 olacak şekilde 11 haneli yazınız."
    )

    password = forms.CharField(
        label="Şifre",
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "********"})
    )
    password_confirm = forms.CharField(
        label="Şifre Tekrar",
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "********"})
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Bu kullanıcı adı zaten alınmış.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu e-posta adresi sistemde zaten kayıtlı.")
        return email

    def clean_telefon(self):
        telefon = self.cleaned_data.get("telefon")
        if telefon:
            if not telefon.startswith('0'):
                raise forms.ValidationError("Telefon numarası '0' ile başlamalıdır.")
            if len(telefon) != 11:
                raise forms.ValidationError("Telefon numarası tam 11 haneli olmalıdır.")
        return telefon

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")

        if p1 and p2:
            if p1 != p2:
                self.add_error("password_confirm", "Şifreler eşleşmiyor.")
            else:
                try:
                    validate_password(p1)
                except ValidationError as e:
                    self.add_error('password', e)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data.get("password"))

        if commit:
            user.save()
            profil, created = Profil.objects.get_or_create(user=user)

            # ❌ okul_numarasi kaldırıldı
            profil.telefon = self.cleaned_data.get("telefon")

            profil.save()

        return user


# --- DİĞER FORMLAR ---
class KullaniciGuncellemeFormu(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

class AdminMassEmailForm(forms.Form):
    subject = forms.CharField(max_length=200, label="Konu", widget=forms.TextInput(attrs={'class': 'vTextField'}))
    message = forms.CharField(label="Mesaj", widget=forms.Textarea(attrs={'rows': 8, 'class': 'vLargeTextField'}))
    is_html = forms.BooleanField(required=False, initial=False, label="HTML olarak gönder")

class ProfilGuncellemeFormu(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ["telefon", "resim"]  # ❌ okul_numarasi kaldırıldı
        widgets = {
            "telefon": forms.TextInput(attrs={"class": "form-control", "maxlength": "11"}),
            "resim": forms.FileInput(attrs={"class": "form-control"}),
        }

class ArizaFormu(forms.ModelForm):
    class Meta:
        model = Ariza
        fields = ["aciklama"]
        widgets = {
            "aciklama": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Arıza detayını yazınız..."})
        }
