import os
import sys

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, Group
from app.database import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def main():
    # Get all users who are leaders
    leaders = db.query(User).join(Group, Group.leader_id == User.id).distinct().all()
    
    print("\nAvailable Leaders:")
    print("-----------------")
    for leader in leaders:
        groups = db.query(Group).filter(Group.leader_id == leader.id).all()
        print(f"ID: {leader.id}")
        print(f"Email: {leader.email}")
        print(f"Groups: {[group.name for group in groups]}")
        print("-----------------")

if __name__ == "__main__":
    main() 