from app import db


class SiteConfig(db.Model):
    __tablename__ = 'site_config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)

    @staticmethod
    def get(key, default=None):
        config = SiteConfig.query.filter_by(key=key).first()
        return config.value if config else default

    @staticmethod
    def set(key, value):
        config = SiteConfig.query.filter_by(key=key).first()
        if config:
            config.value = value
        else:
            config = SiteConfig(key=key, value=value)
            db.session.add(config)
        db.session.commit()
