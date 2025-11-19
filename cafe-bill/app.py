import os
from flask import Flask, request, jsonify
from flasgger import Swagger
from models import db, Masa, SiparisKalemi, get_masa_toplam_tutar

app = Flask(__name__)

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Swagger config
swagger = Swagger(app)

# DB init
db.init_app(app)
with app.app_context():
    try:
        db.create_all()
        print("Veritabanı tabloları hazır.")
    except Exception as e:
        print(f"DB hatası: {e}")

@app.route('/')
def home():
    """
    Ana Sayfa
    ---
    responses:
      200:
        description: API çalışıyor
    """
    return jsonify({"message": "SmartBill API Çalışıyor", "status": "active"})

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
              type: integer
            masa_adi:
              type: string
    responses:
      201:
        description: Masa oluşturuldu
      400:
        description: Hatalı istek
    """
    data = request.get_json()
    masa_id = data.get('id')
    masa_adi = data.get('masa_adi')

    if not masa_id or not masa_adi:
        return jsonify({"error": "id ve masa_adi gereklidir"}), 400

    if Masa.query.get(masa_id):
        return jsonify({"error": "Bu ID ile bir masa zaten var"}), 400

    yeni_masa = Masa(id=masa_id, masa_adi=masa_adi)
    db.session.add(yeni_masa)
    db.session.commit()

    return jsonify({"message": "Masa başarıyla oluşturuldu", "masa": str(yeni_masa)}), 201

@app.route('/masalar', methods=['GET'])
def masalari_getir():
    """
    Tüm Masaları Listele
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
        ozet.append({
            "id": masa.id,
            "ad": masa.masa_adi,
            "toplam_siparis_tutari": round(toplam_siparis, 2),
            "odenen_tutar": round(masa.odenen_tutar, 2),
            "kalan_bakiye": round(kalan_odeme, 2),
            "durum": "Müsait" if kalan_odeme <= 0 and toplam_siparis == 0 else "Dolu"
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
              type: integer
            urun_adi:
              type: string
            tutar:
              type: number
    responses:
      201:
        description: Sipariş eklendi
      400:
        description: Hatalı istek
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
    Ödeme Yap
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            masa_id:
              type: integer
            tutar:
              type: number
    responses:
      200:
        description: Ödeme alındı
      400:
        description: Hatalı istek
      404:
        description: Masa bulunamadı
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

@app.route('/masalar/<int:masa_id>/sifirla', methods=['DELETE'])
def masayi_sifirla(masa_id):
    """
    Masayı Sıfırla
    ---
    parameters:
      - in: path
        name: masa_id
        type: integer
        required: true
        description: Masa ID
    responses:
      200:
        description: Masa sıfırlandı
      404:
        description: Masa bulunamadı
    """
    masa = Masa.query.get(masa_id)
    if not masa:
        return jsonify({"error": "Masa bulunamadı"}), 404

    SiparisKalemi.query.filter_by(masa_id=masa_id).delete()
    masa.odenen_tutar = 0.0
    db.session.commit()

    return jsonify({"message": f"{masa.masa_adi} sıfırlandı ve yeni müşteriye hazır."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
