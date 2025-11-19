import os
from flask import Flask, request, jsonify
from flasgger import Swagger
# models dosyasından db ve diğer sınıfları çekiyoruz
from models import db, Masa, SiparisKalemi, get_masa_toplam_tutar

app = Flask(__name__)

# --- Yapılandırma ---
# Docker Compose'dan gelen DATABASE_URL'i kullanır
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Swagger'ı başlat
swagger = Swagger(app)

# --- Veritabanı Bağlantısı ---
# db nesnesini Flask uygulamasıyla (app) başlatıyoruz
db.init_app(app)

# Uygulama başlarken tabloları oluştur (Migration yerine hızlı çözüm)
with app.app_context():
    try:
        db.create_all()
        print("--- Veritabanı tabloları başarıyla oluşturuldu/kontrol edildi ---")
    except Exception as e:
        print(f"--- DB Bağlantı Hatası: {e} ---")

# --- Route'lar ---

@app.route('/')
def home():
    """
    Ana Sayfa Kontrolü
    ---
    responses:
      200:
        description: API çalışıyor
    """
    return jsonify({"message": "SmartBill API Calisiyor", "status": "active"})

@app.route('/masalar', methods=['POST'])
def masa_olustur():
    """
    Yeni Masa Oluştur
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            id:
              type: string
              example: "Masa-1"
            masa_adi:
              type: string
              example: "Bahçe Masa 1"
    responses:
      201:
        description: Masa oluşturuldu
      400:
        description: Hatalı istek veya ID zaten var
    """
    data = request.get_json()
    masa_id = data.get('id') # String bekliyoruz
    masa_adi = data.get('masa_adi')

    if not masa_id or not masa_adi:
        return jsonify({"error": "id ve masa_adi gereklidir"}), 400

    # Veritabanında bu ID var mı kontrolü
    mevcut_masa = Masa.query.get(masa_id)
    if mevcut_masa:
        return jsonify({"error": f"'{masa_id}' ID'li masa zaten mevcut"}), 400

    yeni_masa = Masa(id=masa_id, masa_adi=masa_adi)
    db.session.add(yeni_masa)
    db.session.commit()

    return jsonify({"message": "Masa başarıyla oluşturuldu", "masa_id": yeni_masa.id}), 201

@app.route('/masalar', methods=['GET'])
def masalari_getir():
    """
    Tüm Masaları ve Durumlarını Listele
    ---
    responses:
      200:
        description: Masalar listelendi
    """
    masalar = Masa.query.all()
    ozet = []
    for masa in masalar:
        toplam_siparis = get_masa_toplam_tutar(masa.id)
        kalan_odeme = toplam_siparis - masa.odenen_tutar
        
        # Yuvarlama işlemi
        ozet.append({
            "id": masa.id,
            "ad": masa.masa_adi,
            "toplam_siparis_tutari": round(toplam_siparis, 2),
            "odenen_tutar": round(masa.odenen_tutar, 2),
            "kalan_bakiye": round(kalan_odeme, 2),
            "durum": "Musait" if kalan_odeme <= 0 and toplam_siparis == 0 else "Dolu"
        })
    return jsonify(ozet)

@app.route('/siparis', methods=['POST'])
def siparis_ekle():
    """
    Sipariş Ekle
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            masa_id:
              type: string
              example: "Masa-1"
            urun_adi:
              type: string
              example: "Cay"
            tutar:
              type: number
              example: 15.50
    responses:
      201:
        description: Sipariş eklendi
      404:
        description: Masa bulunamadı
    """
    data = request.get_json()
    masa_id = data.get('masa_id')
    urun_adi = data.get('urun_adi')
    tutar = data.get('tutar')

    if not all([masa_id, urun_adi, tutar]):
        return jsonify({"error": "masa_id, urun_adi ve tutar gereklidir"}), 400

    masa = Masa.query.get(masa_id)
    if not masa:
        return jsonify({"error": "Masa bulunamadı"}), 404

    yeni_siparis = SiparisKalemi(ad=urun_adi, tutar=float(tutar), masa_id=masa_id)
    db.session.add(yeni_siparis)
    db.session.commit()

    return jsonify({
        "message": "Sipariş eklendi",
        "masa": masa.masa_adi,
        "urun": urun_adi,
        "fiyat": tutar
    }), 201

@app.route('/odeme', methods=['POST'])
def odeme_yap():
    """
    Ödeme Al
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            masa_id:
              type: string
              example: "Masa-1"
            tutar:
              type: number
              example: 50.0
    responses:
      200:
        description: Ödeme işlendi
    """
    data = request.get_json()
    masa_id = data.get('masa_id')
    odenen_miktar = data.get('tutar')

    if not masa_id or not odenen_miktar:
        return jsonify({"error": "masa_id ve tutar gereklidir"}), 400

    masa = Masa.query.get(masa_id)
    if not masa:
        return jsonify({"error": "Masa bulunamadı"}), 404

    masa.odenen_tutar += float(odenen_miktar)
    db.session.commit()

    toplam_borc = get_masa_toplam_tutar(masa_id)
    kalan = toplam_borc - masa.odenen_tutar

    return jsonify({
        "message": "Ödeme alındı",
        "odenen": odenen_miktar,
        "guncel_kalan_borc": round(kalan, 2)
    })

# DİKKAT: Buradaki <int:masa_id> kısmını sildim, sadece <masa_id> yaptım.
# Çünkü senin Masa modelinde ID string (örn: "masa1").
@app.route('/masalar/<masa_id>/sifirla', methods=['DELETE'])
def masayi_sifirla(masa_id):
    """
    Masayı Sıfırla (Hesabı Kapat)
    ---
    parameters:
      - in: path
        name: masa_id
        type: string
        required: true
        description: Masa ID
    responses:
      200:
        description: Masa sıfırlandı
    """
    masa = Masa.query.get(masa_id)
    if not masa:
        return jsonify({"error": "Masa bulunamadı"}), 404

    # İlişkili siparişleri sil (SQLAlchemy cascade ayarı yoksa manuel silmek gerekir)
    SiparisKalemi.query.filter_by(masa_id=masa_id).delete()
    
    masa.odenen_tutar = 0.0
    db.session.commit()

    return jsonify({"message": f"{masa.masa_adi} ({masa.id}) sıfırlandı ve yeni müşteriye hazır."})

if __name__ == '__main__':
    # Docker için host='0.0.0.0' zorunludur.
    app.run(host='0.0.0.0', port=5000, debug=True)
