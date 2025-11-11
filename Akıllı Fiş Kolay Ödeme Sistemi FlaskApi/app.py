from flask import Flask
from flask_restx import Api, Resource, fields, reqparse, Namespace
import time
import random

# --- Flask ve Swagger (flask-restx) Başlatma ---
app = Flask(__name__)
# API'mize bir başlık ve açıklama ekleyerek Swagger sayfasını özelleştiriyoruz
api = Api(app, 
          version='1.0', 
          title='Akıllı Fiş Kolay Ödeme Sistemi API',
          description='Bu API, Akıllı Fiş sistemi için gerekli olan masa hesabı alma ve ödeme yapma işlemlerini simüle eder.')

# Namespace (Alan Adı): API'mizi daha organize hale getirmek için.
# Swagger UI'da endpoint'leri bu başlık altında gruplayacak.
payment_ns = api.namespace('cafe', description='Masa ve Ödeme İşlemleri')


# --- Mock (Taklit) Veritabanı ---
# Gerçek bir veritabanı yerine, sunucu çalıştığı sürece hafızada tutulan
# basit bir Python dictionary'si kullanıyoruz.
MOCK_MASALAR_DB = {
    'masa_101': {
        'masa_adi': 'Bahçe - 1',
        'toplam_tutar': 850.00,
        'odenen_tutar': 150.00,
        'siparisler': [
            {'ad': '2x Türk Kahvesi', 'tutar': 180.00},
            {'ad': '1x Cheesecake', 'tutar': 220.00},
            {'ad': '1x Büyük Su', 'tutar': 50.00},
            {'ad': '2x Çay', 'tutar': 200.00},
            {'ad': '1x Gözleme', 'tutar': 200.00}
        ]
    },
    'masa_102': {
        'masa_adi': 'İç Salon - 5',
        'toplam_tutar': 320.00,
        'odenen_tutar': 0.00,
        'siparisler': [
            {'ad': '1x Latte', 'tutar': 160.00},
            {'ad': '1x Kruvasan', 'tutar': 160.00}
        ]
    }
}

# Cafe POS sistemine giden logları simüle etmek için bir liste
MOCK_CAFE_POS_LOG = []


# --- API Modelleri (Swagger Dokümantasyonu için) ---
# Swagger'ın Girdi (Input) ve Çıktı (Output) verilerinin neye benzeyeceğini
# bilmesi için bu modelleri tanımlıyoruz.

siparis_model = api.model('SiparisKalemi', {
    'ad': fields.String(description='Siparişin adı', example='2x Türk Kahvesi'),
    'tutar': fields.Float(description='Kalemin toplam tutarı', example=180.00)
})

masa_hesap_model = api.model('MasaHesapDetayi', {
    'masa_adi': fields.String(description='Masanın adı', example='Bahçe - 1'),
    'toplam_tutar': fields.Float(description='Hesabın toplamı'),
    'odenen_tutar': fields.Float(description='Şu ana kadar ödenen tutar'),
    'kalan_tutar': fields.Float(description='Ödenmesi gereken kalan tutar'),
    'siparisler': fields.List(fields.Nested(siparis_model))
})

# --- Diyagram Adım 6: POST /odemeBaslat için Girdi Modeli ---
odeme_input_model = api.model('OdemeInput', {
    'tutar': fields.Float(required=True, description='Ödenmek istenen tutar', example=100.50),
    'kart_sahibi': fields.String(required=True, description='Kart sahibinin adı', example='Zübeyde Nur Topalak'),
    'kart_numarasi': fields.String(required=True, description='(Mock) Kart Numarası', example='1234-5678-9012-3456'),
    'son_kullanma_ay': fields.Integer(required=True, description='(Mock) SKT Ay', example=12),
    'son_kullanma_yil': fields.Integer(required=True, description='(Mock) SKT Yıl', example=2028),
    'cvc': fields.String(required=True, description='(Mock) CVC', example='123')
})

# --- Diyagram Adım 11 & 12: Ödeme Sonuç Modeli ---
odeme_sonuc_model = api.model('OdemeSonucu', {
    'basarili': fields.Boolean(description='Ödemenin başarılı olup olmadığı'),
    'mesaj': fields.String(description='İşlem sonucu mesajı', example='Ödeme başarıyla alındı.'),
    'islem_referans_no': fields.String(description='(Mock) Iyzico işlem referansı', example='iyz_123abc456'),
    'guncel_kalan_tutar': fields.Float(description='Ödeme sonrası masada kalan tutar')
})


# --- API Endpoint'leri (Resource'lar) ---

# --- Diyagram Adım 2: GET /masaHesabi?id=[masaID] ---

# 'reqparse' kullanarak URL'deki query parametresini (?id=...) tanımlıyoruz
hesap_parser = reqparse.RequestParser()
hesap_parser.add_argument('id', type=str, required=True, help='Hesabı getirilecek masa ID', location='args')

@payment_ns.route('/masaHesabi')
@payment_ns.expect(hesap_parser) # Swagger'a 'id' parametresinin zorunlu olduğunu bildirir
class MasaHesabi(Resource):
    
    @payment_ns.doc('get_masa_hesabi')
    @payment_ns.marshal_with(masa_hesap_model) # Başarılı yanıtta bu modeli döndürür
    @payment_ns.response(404, 'Masa bulunamadı') # Hata durumunu Swagger'a bildirir
    def get(self):
        """
        [Adım 2 & 3] Müşterinin QR koddan okuttuğu masa ID'sine ait hesap detaylarını getirir.
        """
        args = hesap_parser.parse_args()
        masa_id = args['id']
        
        if masa_id in MOCK_MASALAR_DB:
            # Masayı "veritabanından" çek
            masa_datasi = MOCK_MASALAR_DB[masa_id]
            
            # Kalan tutarı hesapla
            kalan_tutar = masa_datasi['toplam_tutar'] - masa_datasi['odenen_tutar']
            
            # Modeli hazırla ve döndür (Diyagram Adım 3)
            response_data = {
                'masa_adi': masa_datasi['masa_adi'],
                'toplam_tutar': masa_datasi['toplam_tutar'],
                'odenen_tutar': masa_datasi['odenen_tutar'],
                'kalan_tutar': round(kalan_tutar, 2), # Küsüratları yuvarla
                'siparisler': masa_datasi['siparisler']
            }
            return response_data, 200
        else:
            # Masa bulunamazsa 404 hatası döndür
            return {'message': f"'{masa_id}' ID'li masa bulunamadı."}, 404


# --- Diyagram Adım 6: POST /odemeBaslat ---

@payment_ns.route('/odemeBaslat/<string:masa_id>') # masa_id'yi URL'den alalım (daha RESTful)
@payment_ns.param('masa_id', 'Ödeme yapılacak masa ID (örn: masa_101)')
class OdemeBaslat(Resource):

    @payment_ns.doc('post_odeme_baslat')
    @payment_ns.expect(odeme_input_model) # Body'de ne beklediğimizi Swagger'a bildirir
    @payment_ns.response(200, 'Ödeme Başarılı', odeme_sonuc_model)
    @payment_ns.response(400, 'Ödeme Başarısız / Geçersiz İstek', odeme_sonuc_model)
    @payment_ns.response(404, 'Masa bulunamadı')
    def post(self, masa_id):
        """
        [Adım 6-12] Müşteriden alınan tutar ve (mock) kart bilgileri ile ödeme işlemini başlatır.
        """
        
        # 1. Masa var mı kontrol et
        if masa_id not in MOCK_MASALAR_DB:
            return {'message': f"'{masa_id}' ID'li masa bulunamadı."}, 404
            
        masa_datasi = MOCK_MASALAR_DB[masa_id]
        
        # 2. Gelen veriyi (payload) al
        odeme_bilgileri = api.payload
        odenecek_tutar = odeme_bilgileri['tutar']
        
        # 3. Basit bir doğrulama: Kalan tutardan fazla ödeme yapmaya çalışmasın
        kalan_tutar = masa_datasi['toplam_tutar'] - masa_datasi['odenen_tutar']
        if odenecek_tutar > kalan_tutar:
            return {
                'basarili': False,
                'mesaj': f'Girilen tutar (₺{odenecek_tutar}), kalan tutardan (₺{kalan_tutar}) fazla olamaz.',
                'islem_referans_no': None,
                'guncel_kalan_tutar': kalan_tutar
            }, 400 # 400 Bad Request
        
        
        # --- (SIMÜLASYON) ---
        # --- Diyagram Adım 7: Ödeme Ağ Geçidi (Iyzico) ile konuşma ---
        print(f"[{masa_id}] Iyzico'ya ₺{odenecek_tutar} tutarında ödeme isteği gönderiliyor...")
        # (Burada gerçekte Iyzico API'sine istek atılır)
        time.sleep(1) # Simülasyon için 1 saniye bekle
        
        # --- Diyagram Adım 8: Ödeme Durumu (Başarılı/Başarısız) ---
        # Basit bir simülasyon: CVC '999' ise başarısız olsun, diğer her durumda başarılı olsun.
        is_payment_successful = odeme_bilgileri['cvc'] != '999'
        
        if is_payment_successful:
            # --- Ödeme Başarılıysa (alt senaryosu) ---
            
            # --- Diyagram Adım 9: OdemeyiKaydet (CafePOS) ---
            print(f"[{masa_id}] Ödeme BAŞARILI. CafePOS sistemine bildiriliyor...")
            pos_log_entry = {
                'masa_id': masa_id,
                'odenen_tutar': odenecek_tutar,
                'timestamp': time.ctime()
            }
            MOCK_CAFE_POS_LOG.append(pos_log_entry)
            
            # --- Diyagram Adım 13: Masa Bakiyesini Güncelle (Bizim DB'de) ---
            MOCK_MASALAR_DB[masa_id]['odenen_tutar'] += odenecek_tutar
            print(f"[{masa_id}] Veritabanı güncellendi. Yeni ödenen: ₺{MOCK_MASALAR_DB[masa_id]['odenen_tutar']}")

            # --- Diyagram Adım 11: "Ödeme Başarılı" Ekranı (Telefona yanıt) ---
            guncel_kalan = MOCK_MASALAR_DB[masa_id]['toplam_tutar'] - MOCK_MASALAR_DB[masa_id]['odenen_tutar']
            
            return {
                'basarili': True,
                'mesaj': 'Ödemeniz başarıyla alınmıştır. Teşekkür ederiz.',
                'islem_referans_no': f'iyz_{random.randint(10000, 99999)}',
                'guncel_kalan_tutar': round(guncel_kalan, 2)
            }, 200
            
        else:
            # --- Ödeme Başarısızsa (else senaryosu) ---
            print(f"[{masa_id}] Ödeme BAŞARISIZ. (CVC 999 girildi).")
            
            # --- Diyagram Adım 12: "Ödeme Başarısız" Ekranı (Telefona yanıt) ---
            return {
                'basarili': False,
                'mesaj': 'Ödeme reddedildi. Lütfen kart bilgilerinizi kontrol edin veya bankanızla iletişime geçin.',
                'islem_referans_no': None,
                'guncel_kalan_tutar': round(kalan_tutar, 2)
            }, 400


# --- Sunucuyu Çalıştırma ---
if __name__ == '__main__':
    # debug=True sayesinde kodda değişiklik yaptığınızda sunucu kendi kendine yeniden başlar
    app.run(debug=True, port=5000)