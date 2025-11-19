from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()

# Masaların ana verilerini tutar.
class Masa(db.Model):
    __tablename__ = 'masa'
    
    # Masa ID'si (örn: masa_101)
    id = db.Column(db.String(50), primary_key=True)
    # Masanın kullanıcı dostu adı (örn: Köşe Masa 101)
    masa_adi = db.Column(db.String(100), nullable=False)
    # Şu ana kadar ödenen toplam tutar
    odenen_tutar = db.Column(db.Float, default=0.0)
    
    # Siparişler ilişkisi
    siparisler = db.relationship('SiparisKalemi', backref='masa', lazy=True)

    def __repr__(self):
        return f'<Masa {self.id} - {self.masa_adi}>'

# Her bir sipariş kalemini (ürünü) tutar.
class SiparisKalemi(db.Model):
    __tablename__ = 'siparis_kalemi'
    
    id = db.Column(db.Integer, primary_key=True)
    # Sipariş edilen ürün adı (örn: Espresso)
    ad = db.Column(db.String(100), nullable=False)
    # Ürünün fiyatı
    tutar = db.Column(db.Float, nullable=False)
    # Hangi masaya ait olduğu
    masa_id = db.Column(db.String(50), db.ForeignKey('masa.id'), nullable=False)

    def __repr__(self):
        return f'<Siparis {self.ad} - {self.tutar} TL>'

# Yardımcı Fonksiyon: Masa Toplam Hesabını Hesaplama
def get_masa_toplam_tutar(masa_id):
    """Bir masanın siparişlerinin toplam tutarını veritabanından hesaplar."""
    # SiparisKalemi tablosunda ilgili masa ID'sine ait tutarları toplar
    total = db.session.query(func.sum(SiparisKalemi.tutar)).filter_by(masa_id=masa_id).scalar()
    return total if total is not None else 0.0
