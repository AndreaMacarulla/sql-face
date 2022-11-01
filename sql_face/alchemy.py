# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_alchemy.ipynb.

# %% auto 0
__all__ = ['get_session']

# %% ../nbs/02_alchemy.ipynb 3
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# %% ../nbs/02_alchemy.ipynb 4
def get_session(
    output_dir:str, # Output directory
    db_name:str, # .db file name
                    ):  
    db_path = os.path.join(output_dir,db_name+'.db')       
    engine = create_engine(f"sqlite:///{db_path}")
    if not os.path.exists(db_path):
        if not os.path.exists(output_dir):
            print(f'Creating output directory at {output_dir}')
            os.mkdir(output_dir)
            
        print(f'Creating Db file at {db_path}')
        Base.metadata.create_all(engine)

    Session = sessionmaker()
    Session.configure(bind=engine)
    session = Session()
    return session
