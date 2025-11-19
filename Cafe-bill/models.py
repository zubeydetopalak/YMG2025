
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# db nesnesini burada boş olarak oluşturuyoruz.
# app.py içinde bunu dolduracağız.
db = SQLAlchemy()

class Masa(db.Model):
    __tablename__ = 'masa'
    
    # ID String olarak tanımlı (Örn: 'Masa-1', 'Bahce-2' veya sadece '1')
    id = db.Column(db.String(50), primary_key=True)
    masa_adi = db.Column(db.String(100), nullable=False)
    odenen_tutar = db.Column(db.Float, default=0.0)
    
    siparisler = db.relationship('SiparisKalemi', backref='masa', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Masa {self.id} - {self.masa_adi}>'

class SiparisKalemi(db.Model):
    __tablename__ = 'siparis_kalemi'
    
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    tutar = db.Column(db.Float, nullable=False)
    # ForeignKey Masa.id'ye (String) bağlanmalı
    masa_id = db.Column(db.String(50), db.ForeignKey('masa.id'), nullable=False)

    def __repr__(self):
        return f'<Siparis {self.ad} - {self.tutar} TL>'

def get_masa_toplam_tutar(masa_id):
    # scalar() sonucu None dönebilir, bunu kontrol ediyoruz.
    total = db.session.query(func.sum(SiparisKalemi.tutar)).filter_by(masa_id=masa_id).scalar()
    return total if total is not None else 0.0
