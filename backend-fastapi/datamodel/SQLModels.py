from datetime import datetime
from sqlmodel import Field, Session, SQLModel, create_engine, select, text
from typing import Optional


# create users model that'll grab just one user for the profile

# class Users(SQLModel, table = True):
#     pass


# table = True makes it a table model 
class Video(SQLModel, table=True):

    __tablename__ = "videos"
    __table_args__ = {"schema": "auth"}


    video_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="auth.users.user_id")
    title: str
    file_path: str
    create_dt: Optional[datetime] = None




def connect_music_db(): 
    # extract this away later one 
    database_name = "music_app_db"
    port = "5432"
    username = "joel_music_db"
    address = "localhost" 
    password = "music_password" 
    database_url = (
        f"postgresql+psycopg2://{username}:{password}"
        f"@{address}:{port}/{database_name}"
    )

    # create 
    return create_engine(database_url)


# def get_user():
#     engine = connect_music_db()
#     with Session(engine) as session:
#         pass 

def get_videos():
    engine = connect_music_db()
    with Session(engine) as session: 
        return session.exec(select(Video)).all()    
    

def get_videos_by_user(user_id: int):
    engine = connect_music_db() 

    with Session(engine) as session: 
        statement = (
            select(Video).
            where(Video.user_id == user_id)
            .order_by(Video.create_dt.desc())
        )

        return session.exec(statement).all()