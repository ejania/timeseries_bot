from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

DB_URI = 'sqlite:///db.sqlite'

Base = declarative_base()

class Balance(Base):
  __tablename__ = 'balances'
  id = Column(Integer, primary_key=True)
  group = Column(String)
  user = Column(String)
  amount = Column(Float)

if __name__ == '__main__':
    engine = create_engine(DB_URI, echo=True)
    Base.metadata.create_all(engine)
